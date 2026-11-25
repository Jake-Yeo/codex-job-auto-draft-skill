# Sign-in on an existing jobs tab

The applicant performs sign-in, sign-up, passwords, password resets, verification and account-provider steps. Never access Gmail or another inbox. Do not enter authentication credentials or navigate alternative login routes.

Inspect the current form. A mixed registration/application screen can have usable profile fields even if it contains a password field. Complete accessible non-credential fields when the applicant has handled credentials, then leave only the actual account action for the applicant. An email-only iCIMS lookup plus privacy checkbox routes to login/creation and is an account gate, not a profile form.

For a real gate, preserve that exact tab **in jobs** and tell the applicant which employer tab needs sign-in without activating it. Record the specific action with `draft_guard.py defer --reason sign-in` and continue with the next accessible jobs tab. When the applicant signs in, re-observe the same tab in the background. Resume it before public forms once the current draft is finished or preserved.

Keep credentials, codes and tokenized authentication links out of notes and generated files. A stale title or a slow dropdown is not proof the session expired. If the employer itself redirects to login, preserve the form evidence and leave authentication to the applicant.
