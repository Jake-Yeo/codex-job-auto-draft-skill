# Sign-in on an existing jobs tab

The applicant performs sign-in, sign-up, passwords, password resets, verification and account-provider steps. Never access Gmail or another inbox. Do not enter authentication credentials or navigate alternative login routes.

Inspect the current form and its application fields. A candidate profile may include account credentials alongside contact details, documents, work authorization and other questions. Complete all accessible non-credential fields and uploads even when the login and password fields are empty. Check the actual next step after filling the page. Leave only the remaining credential or account action to the applicant. An email-only iCIMS lookup plus privacy checkbox routes to login or account creation.

For a real gate, preserve that exact tab **in jobs** and tell the applicant which employer tab needs sign-in without activating it. Record the specific action with `draft_guard.py defer --reason sign-in` and continue with the next accessible jobs tab. When the applicant says they signed in, inspect the exact live requisition and its current frame immediately. Resume any accessible fields in that form even if the recovery marker still says sign-in. If sign-in took them to the employer’s dashboard, use the observed **Continue Application** for the supplied requisition on that same tab.

Keep credentials, codes and tokenized authentication links out of notes and generated files. A stale title or a slow dropdown is not proof the session expired. If the employer itself redirects to login, preserve the form evidence and leave authentication to the applicant.
