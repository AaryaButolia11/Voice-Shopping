// Backend location.
// - Leave empty ("") for a single-service deploy where FastAPI serves this
//   frontend (same origin). This is the default and needs no changes.
// - For a split deploy (e.g. frontend on Vercel, backend on Render), set this
//   to your backend URL, e.g. "https://your-app.onrender.com".
window.APP_CONFIG = {
  API_BASE: "",
};
