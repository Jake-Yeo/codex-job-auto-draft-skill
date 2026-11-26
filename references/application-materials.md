# Application materials

## Direct browser controls and visual checks

Use the supported browser computer-use controls directly in the existing jobs tab. Inspect the form and screenshots, enter the saved information, and verify the actual values, selections, and uploaded files. The procedures below describe site-specific interactions and recovery.

## Replacing existing field text

Use Path 2’s `fill_input(selector, text, clear_first=True)` to replace existing text when supported. Pasting after a field receives focus can append to its existing value, so preserve the selection when using paste and verify the result before continuing. Use a focused screenshot to check the exact value when the accessibility view redacts it.

On a Workday skills search, if clearing leaves the previous query in place, focus the search input, move to the end, and use Backspace until the input is empty. Verify the empty value before typing the next query. Let the search results settle, select the matching checkbox, and verify the resulting skill chip before continuing.

## Resume and required uploads

Select the applicant's approved documents from the private `documents` module and retain the originals. Inspect each dedicated résumé, cover-letter, transcript, or other upload field and check whether previously attached files remain.

Reinspect the employer form after selection. The filename and the settled attachment state, such as an enabled Remove or Replace control, confirm the upload. A chooser accepting the path, an upload-in-progress label, or a local copy is insufficient. Repeat the attachment check on the final review page and retain the exact generated files for the final chat handoff.

An upload timeout is a reason to inspect the form and repair the interaction. Check whether parsing is still running, the file already appears, or the site reports a type or size error. Look for a portal consent or privacy dialog triggered by the file picker. Confirm the original file exists and the control is for the intended document. Upload the résumé before filling fields when parsing can replace profile values.

Follow the [upload order in the skill](../SKILL.md#fill-check-finish). On Ashby, attach the PDF in the required **Resume** field. **Autofill from resume** is a separate control. For the Path 2 file-picker fallback, locate the observed file input and use `stage_files_once(cdp, session_id, selector, absolute_path)` from `browser_use_cli_form.py`. If the input is in a frame or shadow tree, resolve that input’s node in the correct CDP session and call `cdp("DOM.setFileInputFiles", session_id=frame_session, files=[absolute_path], backendNodeId=input_node)` once. Workday and Scope can clear the input after accepting the file. Inspect the visible upload state or staged filename before retrying; an empty input alone can cause a duplicate upload. If approval remains pending or the input rejects the file, continue the accessible fields and preserve the remaining attachment blocker if recovery fails.

When using the file picker, use the visible **Choose file** label to identify its associated input if the input is hidden, as on Workable. In an embedded iCIMS form, if the **My Computer** button does not bring up the chooser, locate the observed file input inside its iframe and set the file through CDP in that frame. Verify the attached filename after parsing.

On Fitzii, **View Job Posting** opens a modal over the current form. Close it before attaching files. If you need the file picker, use the visible résumé or cover-letter drop area after closing the modal. Verify each filename in its own box. Check for short-answer fields revealed by skill ratings. If a custom Fitzii radio button or checkbox ignores its accessibility click, click the visible circle in a fresh screenshot and verify the selected state.

For embedded Greenhouse forms, leave the employer page open and target the observed iframe through the attachment extension. Check the settled filename in that frame before trying another upload.

Keep embedded uploads in the original browser tab. Opening an application iframe URL directly can lose the draft context. Use browser-scoped controls on the original tab.

If the browser tool loses its connection, recover the original tab by ID as described in [tab recovery](tab-workflow.md).

### Verify iCIMS documents on later steps

On iCIMS, use the résumé field first because choosing a file can trigger parsing and reload the profile. Let it settle before filling other answers or selecting the cover letter. Reinspect the actual requisition, which documents survived, and which fields need filling. If parsing returns to the welcome page, recover the same job through the portal’s visible controls. Finish the accessible fields and retry the missing résumé once the profile is available.

Later questions may hide the upload fields. Verify and save the job-specific answers first. From the signed-in job tab, read the employer’s **Dashboard** and **Update your profile/resume** links in the same session. This is the employer’s own portal. The Path 2 helper checks the exact requisition’s status and compares the saved files in the shared profile without leaving or reloading the draft. Use the local, approved PDFs for comparison. The portal may rename the résumé after parsing.

~~~python
# Run inside the Browser Use Path 2 CLI with <skill-directory>/scripts on sys.path.
from browser_use_cli_icims import inspect_draft

session_id = switch_tab("OBSERVED_TARGET_ID", activate=False)
print(inspect_draft(
    cdp, session_id, "OBSERVED_ICIMS_REQUISITION_URL",
    resume="/absolute/path/to/approved-resume.pdf",
    cover_letter="/absolute/path/to/this-role-cover-letter.pdf",
))
~~~

If the draft is incomplete and the profile holds the wrong cover letter, use its observed **Update your profile/resume** form after the job answers are saved. Keep it in the original tab. If leaving the saved application would open a Chrome prompt, use the observed same-origin profile link in a temporary frame inside that tab so the application stays in place. In that profile form, replace the file in the observed **Cover Letter** field, verify the newly selected filename, and use **Update Profile** to save it. The original résumé can remain when it matches. Try the PDF extension first with the current job URL and observed profile frame path, then use the frame-scoped file input if needed. After the employer confirms the update, remove the temporary frame if used and recheck the original job and the saved PDFs.

Prefer an application-specific cover-letter field whenever offered. If several drafts really share one profile slot, save the answers for every role and keep each tailored PDF. Use the slot for the requested role or the next draft the applicant will submit. Report which letter is in the slot and which other drafts depend on it. A match in the current profile establishes what the profile holds. A receipt for an earlier submission does not establish which file that submission received.

### Replace application documents

Confirm the approved new file and the exact draft selection before using the observed Replace control. Verify the attached filename on the application after replacing. If a separate candidate-profile action deletes a stored document, verify the scope and follow applicable confirmation rules.

### AutoApply attachments

The portable folder includes the PDF attachment extension and its builder. Generate it with `python3 <skill-directory>/scripts/attach_documents.py build` and load the displayed private folder through [Skill setup](setup.html). The helper uses a temporary local connection. Keep the generated extension, bridge token, and PDFs outside the skill folder.

From the live draft, note the tab ID, exact employer URL and each distinct visible file-field label. If the input is in an iframe, pass its observed origin and path as `--frame-url` without embedded tokens. Match the dedicated résumé and cover-letter sections, including when their buttons both say **Attach**. Check for an existing attachment before issuing the command.

~~~python
# In the local Path 2 CLI, with the skill's scripts directory on sys.path.
from attach_documents import main as attachments

attachments([
    "upload", "--tab-id", "TAB_ID", "--url", "OBSERVED_EMPLOYER_URL",
    "--batch-cache", "/path/to/this-batch-temp-dir/upload-bridge.json",
    "--resume-field", "Resume/CV",
    "--cover-letter-field", "Cover Letter", "--cover-letter", "/path/to/approved.pdf",
], cdp=cdp)
~~~

Omit the flags for any document you do not need to attach. The résumé comes from the private profile. A generated letter lives in the private `materials` folder, and an applicant-approved existing one can be saved as `documents.cover_letter`. Use the exact observed labels so the uploader can distinguish both fields. If one upload is blocked, keep filling and use the browser file picker for that PDF if permitted. Use the browser file picker for non-PDFs. Verify actual attachment results on the form before proceeding or retrying.

Path 2 can connect an already enabled **File Upload Helper** that has no bridge credential. It uses an authenticated, temporary connection for the upload. When using a separately configured PDF extension, the first real upload gives that extension its normal connection window, including the extension's polling interval of up to 30 seconds. The configured route also supports the same upload arguments via `python3 scripts/attach_documents.py upload` from the skill directory. Create one temporary directory with `mktemp -d` at the start of the batch and pass the same `--batch-cache` path to each upload. If no extension connects on a route, subsequent attempts through that route return promptly. Inspect the employer form after a delivery error or a field-specific rejection. Use a fresh cache after a Chrome profile change, extension reload, or new batch. For setup or troubleshooting, call `attachments(["check"], cdp=cdp)` to verify the connection without making an upload. An inventory connection alone does not verify the PDF bridge.

## Education and experience

Use the saved education and work entries. Preserve supported dates, title, organization and location. Use office addresses only for employer fields, separately from the applicant's own address. If an expected graduation date is in the future and the widget refuses it, leave the end date open where possible and use a supported description or screening answer for the expected date.

Fill the major or **Field of Study** from `education.field_of_study` whenever the portal offers it. Try the exact major first. Use a catalog equivalent only after checking the settled options. On Workday, verify the committed field of study separately from the school and degree before advancing and on Review.

For Workday month/year steppers, focus and enter each segment with the supported keyboard controls, then move focus away to commit it. Enter a single-digit month without a leading zero when targeting the month segment directly, because the widget can advance to the year as soon as it accepts the month. Enter the month and year through their segment controls to prevent ordinary paste or text fills from misplacing digits. Confirm the displayed month and year, check for date validation errors, and confirm that Save and Continue advances. Verify the date persisted after saving. Use the visible calendar if the segmented controls reject the date.

Workday can display a filled **Role Description** and save it as **No Response** if the input never loses focus. Fill the complete approved descriptions for the observed textarea IDs together with [the batch text helper](browser-workflow.md#batch-controls-on-the-current-page). It moves focus away from each editor and checks the exact text including line breaks. Verify both saved entries on Review. If a description is missing, use the wizard's observed Back controls to repair it in the same draft.

On Workable month/year fields, enter the six digits with the supported sequential key action, then press Escape to close that calendar before opening the next date. Verify the committed month and year, click Update, and check the saved card. If the end-date control rejects future dates for an in-progress degree, leave it open where possible and give the expected graduation date in the relevant screening answer.

Check for entries already imported with the resume before adding anything. Finish each editor and use its Save, Update, or Add control. Verify the institution and employer cards, dates, and descriptions before advancing. Check that returning to a previous page did not reopen an unsaved editor or remove an entry.

### Approved work descriptions

Use only the saved evidence in `experience` or `projects`. Adapt length and emphasis to form limits while preserving the applicant's role, qualifications, and supported outcomes. Avoid conflating a team result with an individual contribution.

When a character limit applies, keep measurable results and delivered scope first. Examples include faster processing times, higher playback capacity, records migrated, and access groups supported. Treat team size as collaboration context when choosing the remaining bullets. Rank quantified bullets by relevance to the role, then use remaining space for the strongest relevant technical contributions. Condense whole points to fit the observed limit and preserve the original figures and qualifiers. Verify the saved description after the editor closes or on Review.

## Skills

Use the complete private `skills` module, including saved additions, plus supported technologies from the current résumé, approved work and project descriptions, and applicant corrections. Read the entire inventory even if the résumé parser imported some tags. Include specific services and protocols alongside broader skills when they represent distinct experience. Search for all supported skills the control can hold. Use the role to order them and to prioritize if the portal enforces a limit. Preserve correct existing chips and merge equivalent spellings. Distinguish tool use and integration from work the applicant has not claimed.

In Workday’s **Type to Add Skills** control, pass the complete inventory to `add_skills` from `browser_use_cli_workday.py`. It replaces each search value, presses Enter, matches the observed choices in that control, and verifies the committed chip. A temporary **No Items** response can disappear as the search settles. Inspect `unavailable` for accurate alternatives and `needs_attention` for results that still need repair; add remaining supported tags where the portal allows them. For a skill requiring manual repair, enter the supported skill and press Enter. If a menu opens, choose the accurate option and verify its selected chip. Keep a longer batch running on this draft, or break the same inventory into consecutive groups within this tab. Save and check the selected skills on Review, expanding **More** when present.

~~~python
# Same attached Path 2 session. Use all saved and verified skills for this applicant.
from browser_use_cli_workday import add_skills

print(add_skills(cdp, session_id, all_supported_skills, field_id="OBSERVED_SKILLS_INPUT_ID"))
~~~

For long searchable Greenhouse dropdowns, type the exact choice to reduce the menu to one result, inspect that result, and press Enter to commit it. Verify the selected value after the menu closes.

For iCIMS custom dropdowns where a click misses, focus the combobox and press Enter to open it. If it has a search box, type the exact choice with `typeText` or `pressSequentially`. Use Down to highlight the verified result, then Enter and check the collapsed value. Wait for a dependent dropdown to update after its parent changes. Ordinary text fields can still use paste or fill.

For SAP SuccessFactors UI5 dropdowns, typing can leave a search value without committing a selection. Open the menu, inspect the settled screenshot, select the visible option, and verify the collapsed value. Follow the [portal save steps](browser-workflow.md#sap-successfactors) to verify it persisted.

## Languages

 Add a row when the portal offers **Languages → Add** and the applicant has a supported entry. Keep correct imported rows. Select the language and complete each applicable fluency, speaking, reading, and writing control revealed by that selection. Use the closest supported proficiency option and verify the saved record on Review or on the last page that shows it. Add all languages user speaks as fluent (or it's equivalent leve), obviously english is always going to be fluent for the user.

The optional `languages` profile module can hold a `languages` list of records containing `language` and `proficiency`. Use separate speaking, reading, or writing values when supplied. Choose the language and level from applicant-specific evidence.

## Websites and profile links

Use the applicant's saved portfolio or website, GitHub, and LinkedIn URLs from `contact` or `contact.links`. If the portal offers repeatable **Websites** or **Professional Links** rows, add one row per distinct saved URL, including GitHub and LinkedIn when the portal also offers dedicated fields for them. Preserve existing correct entries and skip duplicate URLs within the list, treating a trailing slash as equivalent.

Use the dedicated LinkedIn and GitHub fields when offered. If only one generic website field is available, use the saved portfolio or website there. On Workday, verify that each **Add** or **Add Another** action opened a new URL row before entering it. Commit each value, save the section, and verify all saved URLs on Review or on the last page that shows them.

## Cover letters

Follow the narrative and voice guidance in the [cover-letter prompt](cover-letter-prompt.txt), with the applicant's chosen style examples. Use the employer's actual role description, two or three job needs, and relevant evidence from the private profile. Use the employer name and a clean role title in the heading. Leave requisition numbers and internal posting codes out of the letter. Use concrete experience to show why the applicant would be excited to join this employer and team. Describe the engineering skill or other role-specific practice they would like to develop alongside the team and how they could apply a current skill to the same work. Close by explicitly welcoming an interview. Follow the prompt's review steps before rendering. Fit the finished letter on one page. Use an applicant-authored version when the employer requires it.

For a PDF, put the approved letter body on standard input. The portable renderer takes the header's applicant information from the local profile and saves a one-page PDF in its private materials directory. Use the returned path for attachments. Use a separate job key for each application or revision.

~~~sh
uv run --with reportlab --with pypdf python /path/to/job-applications/scripts/cover_letter.py \
  --job-key role-application --company 'Employer' --role 'Readable role title' < letter-body.txt
~~~

The generated filename follows `Company_Short_Role_Applicant_Name_Cover_Letter.pdf`. Use the readable role title in the PDF and a short role in its filename when needed. Follow the employer's requested format. When a site only has a text field, enter the saved prose there and verify it persisted.
