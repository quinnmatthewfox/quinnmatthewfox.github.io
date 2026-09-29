document.getElementById("year").textContent = new Date().getFullYear();

const postsContainer = document.getElementById("posts");
const FEED_URL = "https://quinnmatthewfox.substack.com/feed";
const RSS2JSON_URL = "https://api.rss2json.com/v1/api.json?rss_url=" + encodeURIComponent(FEED_URL);

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function stripHtml(value) {
  const div = document.createElement("div");
  div.innerHTML = value || "";
  return (div.textContent || div.innerText || "").replace(/\s+/g, " ").trim();
}

function makeExcerpt(value, max = 180) {
  const text = stripHtml(value);
  if (text.length <= max) return text;
  return text.slice(0, max - 1).replace(/\s+\S*$/, "") + "…";
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "long",
    year: "numeric"
  }).format(date);
}

function renderPosts(posts) {
  postsContainer.innerHTML = posts.slice(0, 3).map((post) => {
    const date = formatDate(post.date || post.pubDate);
    const description = post.excerpt || makeExcerpt(post.description || post.content || "");
    const url = post.url || post.link;
    return `
      <article class="post-card">
        <p class="post-label">${escapeHtml(date || "Substack")}</p>
        <h3>${escapeHtml(post.title || "Untitled")}</h3>
        ${description ? `<p>${escapeHtml(description)}</p>` : ""}
        <a href="${escapeHtml(url)}" target="_blank" rel="noopener">Read on Substack →</a>
      </article>
    `;
  }).join("");
}

function renderFallback() {
  postsContainer.innerHTML = `
    <article class="post-card">
      <p class="post-label">Newsletter</p>
      <h3>Read the latest writing</h3>
      <p>New poems, stories and notes are published on Substack.</p>
      <a href="https://quinnmatthewfox.substack.com/" target="_blank" rel="noopener">Visit Quinn’s Substack →</a>
    </article>
  `;
}

async function loadSubstackPosts() {
  if (!postsContainer) return;

  // Primary: static JSON refreshed by GitHub Actions.
  try {
    const local = await fetch("posts.json?ts=" + Date.now(), { cache: "no-store" });
    if (local.ok) {
      const data = await local.json();
      if (Array.isArray(data.posts) && data.posts.length) {
        renderPosts(data.posts);
        return;
      }
    }
  } catch (_) {}

  // Secondary: browser-side RSS proxy.
  try {
    const response = await fetch(RSS2JSON_URL, { cache: "no-store" });
    if (!response.ok) throw new Error("Feed proxy unavailable");
    const data = await response.json();
    if (data.status === "ok" && Array.isArray(data.items) && data.items.length) {
      renderPosts(data.items);
      return;
    }
  } catch (_) {}

  renderFallback();
}

loadSubstackPosts();
