export async function typewrite(element, text, speed = 18) {
  if (!element) return;
  element.textContent = "";
  element.classList.add("typewriting");
  for (const char of String(text || "")) {
    element.textContent += char;
    await new Promise((resolve) => setTimeout(resolve, speed));
  }
  element.classList.remove("typewriting");
}
