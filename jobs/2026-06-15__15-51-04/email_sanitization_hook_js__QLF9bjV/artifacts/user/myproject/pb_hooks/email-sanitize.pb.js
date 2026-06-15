// Sanitize the email field on user record creation:
//   - Trim leading/trailing whitespace
//   - Convert to lowercase
//
// This hook only applies to the built-in "users" collection.
onRecordCreateRequest(function (e) {
    var email = e.record.getString("email");
    if (email) {
        var sanitized = email.trim().toLowerCase();
        e.record.set("email", sanitized);
    }
    e.next();
}, "users");
