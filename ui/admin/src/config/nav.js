/**
 * Single source of truth for sidebar nav sections and items.
 * Consumed by main.js (sidebar rendering) and home.js (home page cards).
 *
 * superAdmin: true - item is hidden for non-super-admins
 */
const NAV_SECTIONS = [
  {
    id: "console-access",
    label: "Console Access",
    icon: "lock",
    description: "Configure who can sign in and review their activity",
    items: [
      { view: "users", label: "Manage Users", superAdmin: true },
      { view: "audit-log", label: "Audit Log" },
    ],
  },
  {
    id: "management",
    label: "API Management",
    icon: "stack",
    description: "Manage tenants, keys, blueprints, categories, and extraction rules",
    items: [
      { view: "tenants", label: "Manage Tenants", superAdmin: true },
      { view: "keys", label: "Manage API Keys" },
      { view: "blueprints", label: "Manage Blueprints", superAdmin: true },
      { view: "doc-categories", label: "Manage Document Categories" },
      { view: "extraction-rules", label: "Manage Extraction Rules" },
    ],
  },
  {
    id: "docs",
    label: "Processed Documents",
    icon: "documents",
    description: "Browse and search documents processed through the API",
    items: [
      { view: "documents", label: "Recently Processed" },
      { view: "document-search", label: "Search Documents" },
    ],
  },
  {
    id: "reporting",
    label: "Reporting",
    icon: "chart",
    description: "Track processing performance and API usage over time",
    items: [
      { view: "metrics", label: "Metrics Dashboard" },
      { view: "usage", label: "Usage Tracking" },
    ],
  },
];

export default NAV_SECTIONS;
