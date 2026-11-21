# Application materials

## Direct browser controls and visual checks

Use supported browser controls on the bound tab. Check the actual form after each substantial edit. For embedded uploads, keep the original tab and target its observed application frame. See [same-tab recovery](tab-workflow.md#recover-an-embedded-form-before-deferring) if the connection or input loses focus.

## Replacing existing field text

Replace the exact field's text using a supported control and check the value after it loses focus. For any input with a separate suggestion or Save step, commit the chosen control and verify the final value. Preserve correct existing entries and avoid duplicating parsed experience.

## Resume and required uploads

Select the applicant's approved documents from the private `documents` module and retain the originals. Inspect each dedicated résumé, cover-letter, transcript, or other upload field and check whether previously attached files remain. Verify filenames on the employer page after résumé parsing settles, then recheck answers that changed. Check a screenshot if the form's accessible text omits a filename.

### Replace application documents

Confirm the approved new file and the exact draft selection before using the observed Replace control. Verify the attached filename on the application after replacing. If a separate candidate-profile action deletes a stored document, verify the scope and follow applicable confirmation rules.

### AutoApply attachments

The portable folder includes the PDF attachment extension and its builder. Generate it with `python3 <skill-directory>/scripts/attach_documents.py build` and load the displayed private folder through [Skill setup](setup.html). The helper uses a temporary local connection. Keep the generated extension, bridge token, and PDFs outside the skill folder.

For an active draft, pass the live numeric tab ID, exact observed tab URL, and each distinct visible field label. For an embedded form, add `--frame-url` with the observed frame origin and path. Keep tokens out of persistent notes.

~~~sh
python3 /path/to/job-applications/scripts/attach_documents.py upload \
  --tab-id TAB_ID --url 'OBSERVED_EMPLOYER_URL' \
  --resume-field 'Resume/CV' \
  --cover-letter-field 'Cover Letter' --cover-letter '/path/to/approved.pdf'
~~~

Omit the flags for any document you do not need to attach. The résumé comes from the private profile. A generated letter lives in the private `materials` folder, and an applicant-approved existing one can be saved as `documents.cover_letter`. Use the exact observed labels so the uploader can distinguish both fields. If one upload is blocked, keep filling and use the browser file picker for that PDF if permitted. Use the browser file picker for non-PDFs. Verify actual attachment results on the form before proceeding or retrying.

## Education and experience

Use the saved education and work entries. Preserve supported dates, title, organization and location. Use office addresses only for employer fields, separately from the applicant's own address. If an expected graduation date is in the future and the widget refuses it, leave the end date open where possible and use a supported description or screening answer for the expected date.

For Workday month/year controls, focus and enter each segment, then move focus away to commit it. Check validation and saved values. If a role description saves as **No Response**, return through the observed wizard steps, repair it, move focus away, then verify Review. For Workable month/year controls, commit digits using supported sequential key actions, close the calendar, click Update and verify the card.

Use **Save**, **Update**, or **Add** for each record. Compare imported entries first and verify the saved education, employer, date and description fields afterward.

### Approved work descriptions

Use only the saved evidence in `experience` or `projects`. Adapt length and emphasis to form limits while preserving the applicant's role, qualifications, and supported outcomes. Avoid conflating a team result with an individual contribution.

## Skills

Start with the private `skills` module and supplement from the résumé and confirmed work. Choose the closest accurate tags for the role and retain supported existing chips. Verify each selected option before searching for the next. Distinguish tool use and integration from work the applicant has not claimed.

For Workday **Type to Add Skills**, type a verified skill, press Enter, and wait for the results to settle. Select the exact item if a menu appears, then confirm the chip. For Greenhouse searchable menus, narrow by the exact label and press Enter only after identifying the correct result. For iCIMS select controls, focus the combobox, open with Enter, type the exact choice, then commit the observed option. Follow [SuccessFactors steps](browser-workflow.md#sap-successfactors) for UI5 choices and verify collapsed values and saved sections.

## Cover letters

Follow the narrative and voice guidance in the [cover-letter prompt](cover-letter-prompt.txt), with the applicant's chosen style examples. Use the employer's actual role description, two or three job needs, and relevant evidence from the private profile. Use an exact role and employer name in the heading. Write three or four short paragraphs with one or two concrete experience examples and a warm close. Use an applicant-authored version when the employer requires it.

For a PDF, put the approved letter body on standard input. The portable renderer takes the header's applicant information from the local profile and saves a one-page PDF in its private materials directory. Use the returned path for attachments. Use a separate job key for each application or revision.

~~~sh
uv run --with reportlab --with pypdf python /path/to/job-applications/scripts/cover_letter.py \
  --job-key role-application --company 'Employer' --role 'Exact role title' < letter-body.txt
~~~

The generated filename follows `Company_Short_Role_Applicant_Name_Cover_Letter.pdf`. Use the displayed exact role in the PDF and a short role in its filename when needed. Follow the employer's requested format. When a site only has a text field, enter the saved prose there and verify it persisted.
