# Application materials

## Direct browser controls and visual checks

Use the supported browser computer-use controls directly in the existing jobs tab. Inspect the form and screenshots, enter the saved information, and verify the actual values, selections, and uploaded files. The procedures below describe site-specific interactions and recovery.

## Replacing existing field text

Use the native tab's `setValue` to replace existing text when supported. Pasting after a field receives focus can append to its existing value, so preserve the selection when using paste and verify the result before continuing. Use a focused screenshot to check the exact value when the accessibility view redacts it.

## Resume and required uploads

Select the applicant's approved documents from the private `documents` module and retain the originals. Inspect each dedicated résumé, cover-letter, transcript, or other upload field and check whether previously attached files remain.

Reinspect the employer form after selection. The filename and the settled attachment state, such as an enabled Remove or Replace control, confirm the upload. A chooser accepting the path, an upload-in-progress label, or a local copy is insufficient. Repeat the attachment check on the final review page and retain the exact generated files for the final chat handoff.

An upload timeout is a reason to inspect the form and repair the interaction. Check whether parsing is still running, the file already appears, or the site reports a type or size error. Confirm the original file exists and the control is for the intended document. Upload the résumé before filling fields when parsing can replace profile values.

Follow the [upload order in the skill](../SKILL.md#fill-check-finish). On Ashby, attach the PDF in the required **Resume** field. **Autofill from resume** is a separate control. When using the browser chooser, follow the browser tool’s `file-uploads` guidance. Start `waitForEvent('filechooser')` before clicking the visible Attach or Choose file button and call the chooser’s `setFiles` with the exact absolute path.

When using the file picker, click the visible **Choose file** label if the file input is hidden, as on Workable. In an embedded iCIMS form, if the **My Computer** button does not bring up the chooser, locate the observed file input inside its iframe, arm `waitForEvent('filechooser')`, and press Space on the input. Verify the attached filename after parsing.

On Fitzii, **View Job Posting** opens a modal over the current form. Close it before attaching files. If you need the file picker, use the visible résumé or cover-letter drop area after closing the modal. Verify each filename in its own box. Check for short-answer fields revealed by skill ratings. If a custom Fitzii radio button or checkbox ignores its accessibility click, click the visible circle in a fresh screenshot and verify the selected state.

For embedded Greenhouse forms, leave the employer page open and target the observed iframe through the attachment extension. Check the settled filename in that frame before trying another upload.

Keep embedded uploads in the original browser tab. Opening an application iframe URL directly can lose the draft context. If the native app view shows an unrelated foreground window instead of the expected picker, return to browser-scoped controls on the original tab.

If the browser tool loses its connection, recover the original tab by ID as described in [tab recovery](tab-workflow.md).

### Replace application documents

Confirm the approved new file and the exact draft selection before using the observed Replace control. Verify the attached filename on the application after replacing. If a separate candidate-profile action deletes a stored document, verify the scope and follow applicable confirmation rules.

### AutoApply attachments

The portable folder includes the PDF attachment extension and its builder. Generate it with `python3 <skill-directory>/scripts/attach_documents.py build` and load the displayed private folder through [Skill setup](setup.html). The helper uses a temporary local connection. Keep the generated extension, bridge token, and PDFs outside the skill folder.

From the live draft, note the tab ID, exact employer URL and each distinct visible file-field label. If the input is in an iframe, pass its observed origin and path as `--frame-url` without embedded tokens. Match the dedicated résumé and cover-letter sections, including when their buttons both say **Attach**. Check for an existing attachment before issuing the command.

~~~sh
python3 /path/to/job-applications/scripts/attach_documents.py upload \
  --tab-id TAB_ID --url 'OBSERVED_EMPLOYER_URL' \
  --resume-field 'Resume/CV' \
  --cover-letter-field 'Cover Letter' --cover-letter '/path/to/approved.pdf'
~~~

Omit the flags for any document you do not need to attach. The résumé comes from the private profile. A generated letter lives in the private `materials` folder, and an applicant-approved existing one can be saved as `documents.cover_letter`. Use the exact observed labels so the uploader can distinguish both fields. If one upload is blocked, keep filling and use the browser file picker for that PDF if permitted. Use the browser file picker for non-PDFs. Verify actual attachment results on the form before proceeding or retrying.

## Education and experience

Use the saved education and work entries. Preserve supported dates, title, organization and location. Use office addresses only for employer fields, separately from the applicant's own address. If an expected graduation date is in the future and the widget refuses it, leave the end date open where possible and use a supported description or screening answer for the expected date.

For Workday month/year steppers, focus and enter each segment with the supported keyboard controls, then move focus away to commit it. A painted value is not proof the containing date was saved. Check for date validation errors and confirm Save and Continue advances. Do not use ordinary paste/fill calls for these segmented controls; they can produce invalid months or years. Use the visible calendar if needed, then inspect again.

Workday can display a filled **Role Description** and save it as **No Response** if the input never loses focus. Enter the description and move focus away from the editor before advancing. Verify both entries on Review. If a description is missing, use the wizard's observed Back controls to repair it in the same draft.

On Workable month/year fields, enter the six digits with the supported sequential key action, then press Escape to close that calendar before opening the next date. Verify the committed month and year, click Update, and check the saved card. If the end-date control rejects future dates for an in-progress degree, leave it open where possible and give the expected graduation date in the relevant screening answer.

Check for entries already imported with the resume before adding anything. Finish each editor and use its Save, Update, or Add control. Verify the institution and employer cards, dates, and descriptions before advancing. Check that returning to a previous page did not reopen an unsaved editor or remove an entry.

### Approved work descriptions

Use only the saved evidence in `experience` or `projects`. Adapt length and emphasis to form limits while preserving the applicant's role, qualifications, and supported outcomes. Avoid conflating a team result with an individual contribution.

When a character limit applies, keep measurable results and delivered scope first. Examples include faster processing times, higher playback capacity, records migrated, and access groups supported. Treat team size as collaboration context when choosing the remaining bullets. Rank quantified bullets by relevance to the role, then use remaining space for the strongest relevant technical contributions. Condense whole points to fit the observed limit and preserve the original figures and qualifiers. Verify the saved description after the editor closes or on Review.

## Skills

Start with the private `skills` module and supplement from the résumé and confirmed work. Choose the closest accurate tags for the role and retain supported existing chips. Verify each selected option before searching for the next. Distinguish tool use and integration from work the applicant has not claimed.

In Workday’s **Type to Add Skills** control, type a supported skill and press Enter. A temporary **No Items** result can disappear as the search settles. If Enter opens the results menu, select the matching option. Verify its selected chip before searching for the next skill. Preserve existing chips, save the page, and check the skills on Review, including the **More** list if offered.

For long searchable Greenhouse dropdowns, type the exact choice to reduce the menu to one result, inspect that result, and press Enter to commit it. Verify the selected value after the menu closes.

For iCIMS custom dropdowns where a click misses, focus the combobox and press Enter to open it. If it has a search box, type the exact choice with `typeText` or `pressSequentially`. Use Down to highlight the verified result, then Enter and check the collapsed value. Wait for a dependent dropdown to update after its parent changes. Ordinary text fields can still use paste or fill.

For SAP SuccessFactors UI5 dropdowns, typing can leave a search value without committing a selection. Open the menu, inspect the settled screenshot, select the visible option, and verify the collapsed value. Follow the [portal save steps](browser-workflow.md#sap-successfactors) to verify it persisted.

## Cover letters

Follow the narrative and voice guidance in the [cover-letter prompt](cover-letter-prompt.txt), with the applicant's chosen style examples. Use the employer's actual role description, two or three job needs, and relevant evidence from the private profile. Use an exact role and employer name in the heading. Write three or four short paragraphs with one or two concrete experience examples and a warm close. Use an applicant-authored version when the employer requires it.

For a PDF, put the approved letter body on standard input. The portable renderer takes the header's applicant information from the local profile and saves a one-page PDF in its private materials directory. Use the returned path for attachments. Use a separate job key for each application or revision.

~~~sh
uv run --with reportlab --with pypdf python /path/to/job-applications/scripts/cover_letter.py \
  --job-key role-application --company 'Employer' --role 'Exact role title' < letter-body.txt
~~~

The generated filename follows `Company_Short_Role_Applicant_Name_Cover_Letter.pdf`. Use the displayed exact role in the PDF and a short role in its filename when needed. Follow the employer's requested format. When a site only has a text field, enter the saved prose there and verify it persisted.
