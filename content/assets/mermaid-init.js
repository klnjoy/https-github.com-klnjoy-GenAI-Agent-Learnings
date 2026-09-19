// Give Mermaid diagrams a cleaner look that fits the purple theme.
// Material loads mermaid; we just tweak defaults if it's available.
document.addEventListener("DOMContentLoaded", function () {
  if (window.mermaid && window.mermaid.initialize) {
    try {
      window.mermaid.initialize({
        theme: "base",
        themeVariables: {
          primaryColor: "#ede9fe",
          primaryBorderColor: "#7c4dff",
          primaryTextColor: "#1f2430",
          lineColor: "#6366f1",
          fontFamily: "Inter, system-ui, sans-serif",
        },
        flowchart: { curve: "basis", htmlLabels: true },
      });
    } catch (e) {
      /* non-fatal */
    }
  }
});
