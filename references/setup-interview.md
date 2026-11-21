# Guided setup

For `$job-applications setup` or a submitted `/jobapplication setup` request, resolve the installed skill directory and run `python3 <skill-directory>/scripts/applicant_profile.py setup`. This opens the bundled guide and lists what is missing. Keep setup separate from filling employer forms.

Read the relevant saved modules before asking questions so returning users can resume. Ask one small group at a time and use information the applicant has already supplied. When they provide a résumé, use it for confirmed experience, education, and skills, ask about any uncertain details, and avoid making the applicant type them again.

| Ask about | Save in the private profile |
| --- | --- |
| Application name, email, phone, and city/region/country. Offer to save a mailing address if they use one on forms. | `contact` fields `full_name` (or `first_name` and `last_name`), `email`, `phone`, `location` or `addresses` |
| Where they intend to apply. For each country, ask whether they are authorized to work there and whether they will need sponsorship. Use their answers without inferring eligibility. | `preferences.target_countries` as a list. `eligibility.work_authorization` maps each country to `authorized` and `needs_sponsorship` boolean answers. |
| Local résumé PDF. Ask about optional transcript and other approved materials. Ask for the LinkedIn, portfolio, GitHub, or other links they want to include. | Link documents with `applicant_profile.py link --resume PATH` and optionally `--transcript PATH`. Save links in `contact.links` as an object, even if empty when they say “none.” |
| Education and work history, relevant projects, and skills. Clarify dates and training as needed. | `education`, `experience`, `projects`, and `skills`. Explicit “none” can be saved as an empty list in that section. |
| Application preferences such as target roles, availability, and relocation. Ask for pay expectations only if they want to save one. | `preferences` and `screening`. These details can be answered on individual applications later. |

Save confirmed answers using [the profile workflow](profile-workflow.md), then run `applicant_profile.py setup-status`. Keep asking for the next missing group across turns. When the applicant explicitly wants to handle an item later, add its checklist ID to `setup.deferred`. Save the applicant's choices as provided and summarize anything deferred when the interview is complete. Keep passwords, verification codes, and employer-specific agreements outside the profile.

For the PDF upload extension, run `python3 <skill-directory>/scripts/attach_documents.py build` and share its generated directory and [the setup guide](setup.html). The applicant loads that directory from Chrome’s extension settings. If they already installed the extension and it still matches the generated directory, reuse it. When the setup interview is complete, open the private profile and summarize the sections saved and any remaining browser steps.
