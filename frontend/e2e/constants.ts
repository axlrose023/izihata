// Shared between the auth setup project and the admin specs. Playwright refuses
// to let one test file import another, so the path lives in a plain module.
export const ADMIN_STATE = "e2e/.auth/admin.json";
