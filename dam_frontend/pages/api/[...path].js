const { createHandler } = require("../../lib/serverAuth.cjs");

export const config = { api: { bodyParser: false, responseLimit: false } };
export default createHandler();
