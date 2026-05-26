window.LucyTypewriter = {
  run(el, text, delay = 20, onComplete) {
    if (!el || !text) {
      if (onComplete) onComplete();
      return;
    }
    let index = 0;
    el.textContent = "";
    const interval = setInterval(() => {
      index += 1;
      el.textContent = text.slice(0, index);
      if (index >= text.length) {
        clearInterval(interval);
        if (onComplete) onComplete();
      }
    }, delay);
  },

  scan(root = document) {
    root.querySelectorAll(".typewriter-target[data-text]").forEach((el) => {
      const text = el.getAttribute("data-text") || "";
      el.removeAttribute("data-text");
      this.run(el, text);
    });
  },
};

document.addEventListener("DOMContentLoaded", () => {
  window.LucyTypewriter.scan();
});

document.body.addEventListener("htmx:afterSwap", (evt) => {
  if (evt.detail.target?.id === "chat-messages") {
    window.LucyTypewriter.scan(evt.detail.target);
  }
});
