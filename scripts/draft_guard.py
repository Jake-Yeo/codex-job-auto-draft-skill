#!/usr/bin/env python3
"""Keep one active draft and preserve unresolved drafts for later recovery."""

import argparse
from contextlib import contextmanager
from copy import deepcopy
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


from applicant_profile import ProfileStore, default_dir, write_private

DEFAULT = default_dir() / 'active-draft.json'
ICIMS_JOB_PATH = re.compile(r'/jobs/([0-9]+)(?:/[^/]+)?/(?:job|candidate|questions|eeo)/?')


def clean_url(url):
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise ValueError('Use the observed public application URL without credentials.')
    return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))


def draft_url(url):
    parts = urlsplit(clean_url(url))
    path = parts.path
    if parts.hostname.endswith('.myworkdayjobs.com'):
        path = re.sub(r'/apply/(?:applyManually|autofillWithResume)/?$', '/apply', path)
    if parts.hostname == 'icims.com' or parts.hostname.endswith('.icims.com'):
        job = ICIMS_JOB_PATH.fullmatch(path)
        if job:
            path = f'/jobs/{job[1]}'
    return urlunsplit(parts._replace(path=path))


def matches_draft(draft, tab_id, url=None):
    return bool(draft and draft['tab_id'] == tab_id
                and (url is None or draft_url(draft['url']) == draft_url(url)))


def load_state(path):
    empty = {'active': None, 'pending_confirmations': [], 'deferred': []}
    if not path.exists():
        return empty
    value = json.loads(path.read_text(encoding='utf-8'))
    # Preserve markers written before pending confirmations were supported.
    if isinstance(value, dict) and 'tab_id' in value:
        return {**empty, 'active': value}
    if (not isinstance(value, dict) or value.get('version') not in (2, 3)
            or not isinstance(value.get('pending_confirmations'), list)
            or not isinstance(value.get('deferred', []), list)
            or (value.get('active') is not None and not isinstance(value['active'], dict))):
        raise ValueError('Invalid draft guard state; preserve it for recovery.')
    return {key: value.get(key, default) for key, default in empty.items()}


def save_state(path, state):
    if not any(state.values()):
        path.unlink(missing_ok=True)
    else:
        write_private(path, json.dumps({'version': 3, **state}, ensure_ascii=False, indent=2) + '\n')


@contextmanager
def edit_active_draft(path, tab_id, url):
    with ProfileStore(path.parent).locked():
        state = load_state(path)
        active = state['active']
        if not matches_draft(active, str(tab_id), url):
            raise ValueError('The tab and URL must match the active draft.')
        original = deepcopy(active)
        yield active
        if active != original:
            active['updated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
            save_state(path, state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, default=DEFAULT,
                        help='Recovery marker location; use a temporary path for tests.')
    commands = parser.add_subparsers(dest='action', required=True)
    commands.add_parser('status')
    start = commands.add_parser('start')
    start.add_argument('--tab-id', required=True)
    start.add_argument('--url', required=True)
    start.add_argument('--employer', required=True)
    start.add_argument('--role', required=True)
    start.add_argument('--next', required=True)
    note = commands.add_parser('note')
    note.add_argument('--tab-id', required=True)
    note.add_argument('--next', required=True)
    save_flags = note.add_mutually_exclusive_group()
    save_flags.add_argument('--waiting-for-save', action='store_true',
                            help='Keep the draft active while an observed save is pending.')
    save_flags.add_argument('--save-settled', action='store_true',
                            help='Clear a save marker after observing its result on this draft.')
    pending = commands.add_parser('await-confirmation',
                                  help='Preserve an active draft waiting for a required confirmation.')
    pending.add_argument('--tab-id', required=True)
    pending.add_argument('--next', required=True)
    defer = commands.add_parser('defer', help='Preserve a draft with a remaining tab-specific blocker.')
    defer.add_argument('--tab-id', required=True)
    defer.add_argument('--reason', choices=('attachment', 'browser', 'sign-in', 'form'), required=True)
    defer.add_argument('--next', required=True)
    resume = commands.add_parser('resume', help='Resume a preserved draft on its original tab.')
    resume.add_argument('--tab-id', required=True)
    resume.add_argument('--url', help='Observed URL of this application')
    rebind = commands.add_parser('rebind')
    rebind.add_argument('--tab-id', required=True)
    rebind.add_argument('--new-tab-id', required=True)
    rebind.add_argument('--url', help='Observed URL of the same application on the replacement tab')
    finish = commands.add_parser('finish')
    finish.add_argument('--tab-id', required=True)
    finish.add_argument('--url', help='URL of the reviewed application or its saved marker if closed')
    finish.add_argument('--verified', action='store_true', required=True,
                        help='Agent verified final review or confirmed the tab closed or was submitted.')
    args = parser.parse_args()
    with ProfileStore(args.state.parent).locked():
        state = load_state(args.state)
        active = state['active']
        preserved = (state['pending_confirmations'], state['deferred'])
        if args.action in ('start', 'resume', 'finish'):
            active_matches = matches_draft(active, args.tab_id, args.url)
            matches = [(group, item) for group in preserved for item in group
                       if matches_draft(item, args.tab_id, args.url)]
            if int(active_matches) + len(matches) > 1:
                raise ValueError('More than one draft matches this tab. Pass the application URL.')
            saved = matches[0] if matches else None
        if args.action == 'status':
            result = state
        elif args.action == 'start':
            if active and not active_matches:
                raise ValueError('Another draft is active; finish or recover it before starting a new one.')
            if saved:
                raise ValueError('This draft is preserved; use resume on the existing tab.')
            if not active:
                active = {'version': 1, 'tab_id': args.tab_id, 'url': clean_url(args.url),
                          'employer': args.employer, 'role': args.role, 'next': args.next,
                          'updated_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
                state['active'] = active
                save_state(args.state, state)
            result = {'active': active}
        elif args.action == 'resume':
            if active and not active_matches:
                raise ValueError('Another draft is active; finish or preserve it before resuming a draft.')
            if not active:
                if not saved:
                    raise ValueError('No preserved draft matches this tab.')
                group, active = saved
                group.remove(active)
                active.pop('reason', None)
                active['updated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
                state['active'] = active
                save_state(args.state, state)
            result = {'active': active}
        elif args.action == 'finish' and not active_matches:
            if not saved:
                raise ValueError('The tab does not match an active or preserved draft.')
            group, draft = saved
            group.remove(draft)
            save_state(args.state, state)
            result = {'active': active, 'finished_tab_id': args.tab_id}
        else:
            if not active or active['tab_id'] != args.tab_id:
                raise ValueError('The tab does not match the active draft; do not switch applications.')
            if 'save' in active and args.action in ('defer', 'await-confirmation', 'finish'):
                raise ValueError('A save is pending on this draft. Check its result on the same tab.')
            if args.action == 'note':
                if args.waiting_for_save:
                    active.setdefault('save', {})
                elif args.save_settled:
                    active.pop('save', None)
                active['next'] = args.next
                active['updated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
                save_state(args.state, state)
                result = {'active': active}
            elif args.action in ('await-confirmation', 'defer'):
                active['next'] = args.next
                active['updated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
                key = 'pending_confirmations'
                if args.action == 'defer':
                    key = 'deferred'
                    active['reason'] = args.reason
                state[key].append(active)
                state['active'] = None
                save_state(args.state, state)
                result = {'active': None, key: state[key]}
            elif args.action == 'rebind':
                if args.url and not matches_draft(active, args.tab_id, args.url):
                    raise ValueError('The replacement tab URL is for a different application.')
                if any(matches_draft(item, args.new_tab_id, active['url'])
                       for group in preserved for item in group):
                    raise ValueError('The replacement tab already has a marker for this application.')
                active['tab_id'] = args.new_tab_id
                if args.url:
                    active['url'] = clean_url(args.url)
                active['updated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
                save_state(args.state, state)
                result = {'active': active}
            else:
                state['active'] = None
                save_state(args.state, state)
                result = {'active': None, 'finished_tab_id': args.tab_id}
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        raise SystemExit('Draft guard: ' + str(error))
