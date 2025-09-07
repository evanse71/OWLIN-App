/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        owlin: {
          rich: "var(--owlin-rich-black)",
          navy: "var(--owlin-navy-blue)",
          cerulean: "var(--owlin-cerulean)",
          sapphire: "var(--owlin-sapphire)",
          spiro: "var(--owlin-spiro)",
          bg: "var(--owlin-bg)",
          card: "var(--owlin-card)",
          text: "var(--owlin-text)",
          muted: "var(--owlin-muted)",
          stroke: "var(--owlin-stroke)",
          success: "var(--owlin-success)",
          warning: "var(--owlin-warning)",
          danger: "var(--owlin-danger)",
        },
      },
      boxShadow: {
        owlin: "var(--owlin-shadow)",
        "owlin-lg": "var(--owlin-shadow-lg)",
      },
      borderRadius: { owlin: "var(--owlin-radius)" },
      transitionTimingFunction: {
        "owlin-out": "var(--ease-out)",
        "owlin-in": "var(--ease-in)",
      },
      transitionDuration: {
        fast: "var(--dur-fast)",
        med: "var(--dur-med)",
        slow: "var(--dur-slow)",
      },
    },
  },
  plugins: [],
}; 