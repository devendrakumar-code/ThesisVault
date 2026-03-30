import os

path = "frontend/src/components/common/SubmissionReviewModal.vue"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the visibility of the extension days input
old_vif = "v-if=\"form.review_status === 'rejected'\""
new_vif = "v-if=\"['rejected', 'needs_revision'].includes(form.review_status)\""

# 2. Update the helper text
old_text = "The student will see the submission as rejected and can upload a new version until this extended window closes."
new_text = "The student will be notified and can upload a corrected version until this extended window closes."

# 3. Update the payload line (from previous fix or current state)
# Note: I'll handle both my previous attempted fix and the original just in case.
old_payload_orig = "rejection_extension_days: form.value.review_status === 'rejected' ? parseInt(form.value.rejection_extension_days) || 0 : null"
new_payload = "rejection_extension_days: ['rejected', 'needs_revision'].includes(form.value.review_status) ? parseInt(form.value.rejection_extension_days) || 0 : null"

content = content.replace(old_vif, new_vif)
content = content.replace(old_text, new_text)
if old_payload_orig in content:
    content = content.replace(old_payload_orig, new_payload)
else:
    # Try the original boolean version if my previous fix wasn't applied
    old_payload_bool = "rejection_extension_days: form.value.review_status === 'rejected'"
    content = content.replace(old_payload_bool, new_payload)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Fixes applied to SubmissionReviewModal.vue!")
