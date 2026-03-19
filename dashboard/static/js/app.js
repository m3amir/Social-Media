// State
let currentTopic = "";
let currentOffset = 0;
let bookmarkedOnly = false;
let searchTimer = null;
const PAGE_SIZE = 30;

// Init
document.addEventListener("DOMContentLoaded", () => loadPosts());

function filterTopic(btn, topic) {
    document.querySelectorAll(".topic-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentTopic = topic;
    currentOffset = 0;
    loadPosts();
}

function toggleBookmarkFilter() {
    bookmarkedOnly = !bookmarkedOnly;
    document.getElementById("bookmarkFilter").classList.toggle("active", bookmarkedOnly);
    currentOffset = 0;
    loadPosts();
}

function debounceSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
        currentOffset = 0;
        loadPosts();
    }, 300);
}

async function loadPosts(append = false) {
    const sort = document.getElementById("sortSelect").value;
    const search = document.getElementById("searchBox").value.trim();

    const params = new URLSearchParams({
        sort: sort,
        order: "desc",
        limit: PAGE_SIZE,
        offset: currentOffset,
    });
    if (currentTopic) params.set("topic", currentTopic);
    if (bookmarkedOnly) params.set("bookmarked", "true");
    if (search) params.set("search", search);

    if (!append) {
        document.getElementById("postList").innerHTML =
            '<div class="loading"><div class="spinner"></div><p>Loading posts...</p></div>';
    }

    try {
        const resp = await fetch(`/api/posts?${params}`);
        const posts = await resp.json();

        if (!append) {
            document.getElementById("postList").innerHTML = "";
        }

        if (posts.length === 0 && !append) {
            document.getElementById("postList").innerHTML =
                '<div class="empty-state"><p>No posts found.</p><p style="margin-top:8px;font-size:13px;">Try running the scraper first or adjusting your filters.</p></div>';
        }

        posts.forEach(post => {
            document.getElementById("postList").insertAdjacentHTML("beforeend", renderPost(post));
        });

        document.getElementById("loadMore").style.display =
            posts.length >= PAGE_SIZE ? "block" : "none";
    } catch (err) {
        console.error("Failed to load posts:", err);
        if (!append) {
            document.getElementById("postList").innerHTML =
                '<div class="empty-state"><p>Failed to load posts. Is the server running?</p></div>';
        }
    }
}

function loadMore() {
    currentOffset += PAGE_SIZE;
    loadPosts(true);
}

function renderPost(post) {
    const initial = (post.display_name || post.username || "?")[0].toUpperCase();
    const engLevel = post.engagement_score >= 500 ? "high" :
                     post.engagement_score >= 100 ? "mid" : "low";
    const bookmarkClass = post.bookmarked ? "bookmarked" : "";
    const timeStr = formatTime(post.timestamp);

    return `
    <div class="post-card" id="post-${post.id}">
        <div class="post-header">
            <div class="post-author">
                <div class="post-avatar">${escapeHtml(initial)}</div>
                <div>
                    <div class="post-name">${escapeHtml(post.display_name || post.username)}</div>
                    <div class="post-username">@${escapeHtml(post.username)}</div>
                </div>
            </div>
            <span class="post-topic">${escapeHtml(post.topic || "General")}</span>
        </div>
        <div class="post-content">${escapeHtml(post.content)}</div>
        <div class="post-stats">
            <span class="stat likes"><span class="icon">&#9829;</span> ${formatNum(post.likes)}</span>
            <span class="stat retweets"><span class="icon">&#8635;</span> ${formatNum(post.retweets)}</span>
            <span class="stat quotes"><span class="icon">&#10078;</span> ${formatNum(post.quotes)}</span>
            <span class="stat"><span class="icon">&#128172;</span> ${formatNum(post.comments)}</span>
            ${post.impressions ? `<span class="stat impressions"><span class="icon">&#128065;</span> ${formatNum(post.impressions)}</span>` : ''}
            <span class="engagement-badge ${engLevel}">${formatNum(post.engagement_score)} pts</span>
        </div>
        <div class="post-footer">
            <span class="post-time">${timeStr}</span>
            <div class="post-actions">
                <button class="btn-action ${bookmarkClass}" onclick="toggleBookmark(${post.id}, this)">
                    &#9733; Save
                </button>
                <a class="btn-action" href="${escapeHtml(post.url)}" target="_blank" rel="noopener">
                    View on X &#8599;
                </a>
            </div>
        </div>
    </div>`;
}

async function toggleBookmark(postId, btn) {
    try {
        const resp = await fetch(`/api/bookmark/${postId}`, { method: "POST" });
        const data = await resp.json();
        btn.classList.toggle("bookmarked", data.bookmarked);
    } catch (err) {
        console.error("Bookmark failed:", err);
    }
}

function formatNum(n) {
    if (n == null) return "0";
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "K";
    return n.toString();
}

function formatTime(isoStr) {
    if (!isoStr) return "";
    try {
        const d = new Date(isoStr);
        const now = new Date();
        const diffMs = now - d;
        const diffH = Math.floor(diffMs / 3600000);
        if (diffH < 1) return Math.floor(diffMs / 60000) + "m ago";
        if (diffH < 24) return diffH + "h ago";
        if (diffH < 168) return Math.floor(diffH / 24) + "d ago";
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    } catch {
        return isoStr;
    }
}

function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
