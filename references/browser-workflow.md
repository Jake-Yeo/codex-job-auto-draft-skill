# Direct browser workflow

Use supported browser computer-use controls on the single current jobs tab. Inspect each page, fill and verify it, and save non-final sections as available. Keep the draft open and leave final submission to the applicant.

## Complete every applicable control

- Before advancing, inspect required and applicable optional fields, dependent questions, and form validation. Fill fields using the applicant's saved facts and materials. Check the saved choices, attachments, consent boxes, and name and date fields on Review or on the last page where each control is visible.
- Use `self-identification.pronouns` and other saved self-identification answers from the private profile. Match equivalent wording in the form. Never select **Prefer not to answer** or an equivalent opt-out. Assume an optional self-identification field to the best of your abilities if the applicant has supplied no answer.
- For **Current company**, use the applicant’s confirmed current employer. Enter **Student** for an enrolled applicant with no current employer when the field accepts text or offers a matching option.
- For questions about how many internships or internship terms the applicant has completed, count the entries in `experience.completed_internship_terms_months` when saved. Each entry gives one completed term’s length in months. Use the work-history records when the question specifically asks for distinct roles or employers. 4 months count as 1 term, so a 8 month internship is 2 terms.
- For text-message opt-in limited to updates about this application, including status and interview scheduling, select **Yes** when `preferences.application_update_text_messages` is enabled. Read the stated scope before selecting an option.
- Use the applicable approval for that exact action without asking twice. For a combined checkbox, account for each consent it gives. Leave final Apply for the applicant.
- Use the applicant's standing consent to complete ordinary acknowledgments and factual certifications. Fill authorized typed signatures with the applicant’s verified signature name and use the date and format requested by the form. Read enough of the control's label and surrounding text to distinguish a routine acknowledgment from accepting an agreement, signing a waiver, or granting access to sensitive records. When the tool requires confirmation at the time, handle the exact remaining control with the existing `await-confirmation` workflow and continue with accessible work.
- Inspect any **I am not a robot** or **I am human** control in context. An ordinary applicant acknowledgment can be completed as a form field. If verification remains, finish the other fields, save if possible, and keep the exact draft open with that control identified in the handoff.

## Portal troubleshooting

Use the steps that match the controls and errors on the current form. Record new repairs by portal and symptom so they can be reused.

### Workday

- Type the lookup value and press Enter. If it commits immediately, verify the selected chip. If a menu opens, choose the matching option and verify it after closing the menu. For chained source fields, select the accurate category and then its matching detail. If clicking a single-choice row does not commit it, use the visible radio button or exact row in a fresh screenshot. Check the resulting value on Review.
- Follow the [education and experience steps](application-materials.md#education-and-experience) to commit segmented dates and role descriptions. Inspect the same tab if **Save and Continue** takes longer than expected.

### SAP SuccessFactors

- **Profile and draft.** If sign-in opens **Candidate Profile**, complete and save the profile first. Verify contact details, documents, work history, education, and language before opening the matching requisition under **Draft Applications**. If there is no saved draft, start from the supplied posting in the same tab. Confirm the requisition and inherited details, complete the job-specific fields, and leave final **Apply** for the applicant.
- **Saving.** Use the non-final **Save** as early as the form allows and after each substantial section. **Candidate Profile saved successfully** verifies the profile only. Verify that the specific job application shows a draft save, then reopen the changed sections to check their values. For a UI5 form that offers **Close → Save as Draft → OK**, verify the saved draft through its matching **Continue Applying** card.
- **Fields that do not persist.** If a city, country, company, or title displays correctly but is missing or wrong after saving, commit the dependent selections first, enter text through supported keyboard controls, and move focus away before saving. If a date still reports an error after typing, use the visible calendar. Reopen the section and verify every corrected field.
- **Documents.** Use the dedicated tiles in **My Documents** and follow the [attachment steps](application-materials.md#resume-and-required-uploads). If résumé parsing rebuilds the form, let it settle before completing or verifying contact, education, and screening answers. After a sign-in interruption, check which files are present before retrying any upload. Verify filenames and available document controls, then verify the files selected on the application itself.
- **Sessions.** If switching between employers on the same portal domain repeatedly returns to sign-in, have the applicant sign in to the employer currently being worked on. Save and verify that draft before switching. [SAP guidance on simultaneous sessions](https://userapps.support.sap.com/sap/support/knowledge/en/3560157)

### iCIMS

- Distinguish email-only account lookup from an accessible application profile. For searchable dropdowns, typing can trigger options when paste does not. Verify the exact committed selection.
- Verify and save earlier sections as you fill them. If the last question page offers **Next** without making clear that it opens a review page, leave that control for the applicant because it can submit the application.

### Other portals

- **UKG.** Save repeating entries individually. Verify that the intended documents are selected for the application even if the upload picker is empty after attachment.
- **JazzHR.** Opening the **Attach resume** link can reveal an input without opening a chooser. Use the revealed field with the [attachment procedure](application-materials.md#resume-and-required-uploads) and verify the resulting filename.
- **Embedded forms.** Use [same-tab recovery](tab-workflow.md#recover-an-embedded-form-before-deferring) if direct input loses focus inside the application frame.

## UBC Science Co-op Scope

- Work on the existing Scope job tabs first when the applicant requests it. If its session-expiry dialog appears, choose **Stay logged in** or its equivalent immediately. The applicant handles sign-in if the session expires.
- Read each supplied posting's exact job ID, title, employer, addressee and required documents. Create a **new, role-specific application package** for each posting. Reuse verified current supporting documents and create a separate tailored cover letter for each role.
- Under **My Documents**, set the document filter to **all** when looking for older uploads. Open **Upload Document** or the relevant **Upload New** control. Enter a descriptive name, select the correct document type, and follow the [attachment steps](application-materials.md#resume-and-required-uploads). Click **Upload Document** once the file is staged, wait for **Document was uploaded successfully**, and verify that the document appears in the relevant dropdown. Upload the required documents before setting up the application package because uploading from an open package can reset its unsaved name and selections.
- After choosing a file, check for the filename beside **Current File**. Scope can clear the hidden file input while retaining the staged PDF. If **Upload Document** leaves the same form open, inspect the staged file and any error or busy message before retrying the save.
- Use the applicant’s saved résumé and transcript with their uploaded co-op summary. Check stored documents before reusing them. If the portal requires a stored transcript and the upload menu lacks the right category for the current copy, include the required stored transcript and attach the current copy under **Other document as required by job** when allowed. Verify the combined package and tell the applicant if it contains both versions.
- In **My Documents → Create Application Package**, name the package for the exact role and select its résumé, summary sheet, required transcript, tailored cover letter, and any additional documents. The **Submit** button on this standalone package builder creates the package; verify **Package was created successfully**. This step does not itself submit a job application.
- Return to the original posting in the same tab. If needed, use Scope's **Search Posting** with the exact previously observed job ID. On **Apply**, choose **Apply with an existing application package** and select the new package created for that role. Preview the combined PDF to verify the summary, correct employer letter, résumé and transcript pages. Leave **Submit Application** for the applicant. Do not select an old unrelated package or treat a saved package as a submitted application.
