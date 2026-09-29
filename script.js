document.getElementById("year").textContent = new Date().getFullYear();

const postsContainer = document.getElementById("posts");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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

async function loadSubstackPosts() {
  if (!postsContainer) return;

  try {
    const response = await fetch("posts.json", { cache: "no-store" });
    if (!response.ok) throw new Error("Could not load posts");
    const data = await response.json();
    const posts = Array.isArray(data.posts) ? data.posts.slice(0, 3) : [];

    if (!posts.length) throw new Error("No posts available yet");

    postsContainer.innerHTML = posts.map((post) => {
      const date = formatDate(post.date);
      return `
        <article class="post-card">
          <p class="post-label">${date || "Substack"}</p>
          <h3>${escapeHtml(post.title)}</h3>
          ${post.excerpt ? `<p>${escapeHtml(post.excerpt)}</p>` : ""}
          <a href="${escapeHtml(post.url)}" target="_blank" rel="noopener">Read on Substack →</a>
        </article>
      `;
    }).join("");
  } catch (error) {
    postsContainer.innerHTML = `
      <article class="post-card">
        <p class="post-label">Newsletter</p>
        <h3>Read the latest writing</h3>
        <p>New poems, stories and notes are published on Substack.</p>
        <a href="https://quinnmatthewfox.substack.com/" target="_blank" rel="noopener">Visit Quinn’s Substack →</a>
      </article>
    `;
  }
}

loadSubstackPosts();
