// State
let currentTopic = "";
let currentOffset = 0;
let bookmarkedOnly = false;
let searchTimer = null;
let currentReplyPost = null;
const PAGE_SIZE = 30;

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
        sort, order: "desc", limit: PAGE_SIZE, offset: currentOffset,
    });
    if (currentTopic) params.set("topic", currentTopic);
    if (bookmarkedOnly) params.set("bookmarked", "true");
    if (search) params.set("search", search);

    if (!append) {
        document.getElementById("postList").innerHTML =
            '<div class="loading"><div class="spinner"></div><p>Loading...</p></div>';
    }

    try {
        const resp = await fetch(`/api/posts?${params}`);
        const posts = await resp.json();

        if (!append) document.getElementById("postList").innerHTML = "";

        if (posts.length === 0 && !append) {
            document.getElementById("postList").innerHTML =
                '<div class="empty-state"><p>No posts found.</p></div>';
        }

        posts.forEach(post => {
            document.getElementById("postList").insertAdjacentHTML("beforeend", renderPost(post));
        });

        document.getElementById("loadMore").style.display =
            posts.length >= PAGE_SIZE ? "block" : "none";
    } catch (err) {
        if (!append) {
            document.getElementById("postList").innerHTML =
                '<div class="empty-state"><p>Failed to load posts.</p></div>';
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
    const postData = encodeURIComponent(JSON.stringify(post));

    return `
    <div class="post-card" id="post-${post.id}">
        <div class="post-header">
            <div class="post-author">
                <div class="post-avatar">${esc(initial)}</div>
                <div>
                    <div class="post-name">${esc(post.display_name || post.username)}</div>
                    <div class="post-username">@${esc(post.username)}</div>
                </div>
            </div>
            <span class="post-topic">${esc(post.topic || "General")}</span>
        </div>
        <div class="post-content">${esc(post.content)}</div>
        <div class="post-stats">
            <span class="stat">${formatNum(post.likes)} likes</span>
            <span class="stat">${formatNum(post.retweets)} RT</span>
            <span class="stat">${formatNum(post.quotes)} quotes</span>
            <span class="stat">${formatNum(post.comments)} replies</span>
            ${post.impressions ? `<span class="stat">${formatNum(post.impressions)} views</span>` : ''}
            <span class="engagement-badge ${engLevel}">${formatNum(post.engagement_score)}</span>
            ${post.reply_opportunity > 100 ? `<span class="reply-opp-badge">${formatNum(post.reply_opportunity)} opp</span>` : ''}
        </div>
        <div class="post-footer">
            <span class="post-time">${timeStr}</span>
            <div class="post-actions">
                <button class="btn-action" onclick='openReplyModal(${postData})'>Craft reply</button>
                <button class="btn-action ${bookmarkClass}" onclick="toggleBookmark(${post.id}, this)">Save</button>
                <a class="btn-action" href="${esc(post.url)}" target="_blank" rel="noopener">View</a>
            </div>
        </div>
    </div>`;
}

// ── Reply Composer ──────────────────────────────────────────────

function openReplyModal(post) {
    if (typeof post === 'string') post = JSON.parse(decodeURIComponent(post));
    currentReplyPost = post;

    document.getElementById("modalTweet").innerHTML =
        `<div class="modal-tweet-author">@${esc(post.username)}</div>${esc(post.content)}`;
    document.getElementById("insightInput").value = "";
    document.getElementById("generatedReply").textContent = "";
    document.getElementById("generatedReply").classList.remove("visible");
    document.getElementById("btnCopy").classList.remove("visible");
    document.getElementById("replyModal").classList.add("active");
    document.getElementById("insightInput").focus();
}

function closeReplyModal() {
    document.getElementById("replyModal").classList.remove("active");
    currentReplyPost = null;
}

async function generateReply() {
    const insight = document.getElementById("insightInput").value.trim();
    const tone = document.getElementById("toneSelect").value;
    const btn = document.getElementById("btnGenerate");

    if (!insight) {
        document.getElementById("insightInput").placeholder = "Please enter your insight or angle first...";
        return;
    }

    btn.disabled = true;
    btn.textContent = "Generating...";

    try {
        const resp = await fetch("/api/generate-reply", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                tweet_content: currentReplyPost.content,
                tweet_author: currentReplyPost.username,
                insight: insight,
                tone: tone,
            }),
        });

        const data = await resp.json();

        if (data.error) {
            document.getElementById("generatedReply").textContent = "Error: " + data.error;
        } else {
            document.getElementById("generatedReply").textContent = data.reply;
        }
        document.getElementById("generatedReply").classList.add("visible");
        document.getElementById("btnCopy").classList.add("visible");
    } catch (err) {
        document.getElementById("generatedReply").textContent = "Failed to generate reply. Check server logs.";
        document.getElementById("generatedReply").classList.add("visible");
    } finally {
        btn.disabled = false;
        btn.textContent = "Regenerate";
    }
}

function copyReply() {
    const text = document.getElementById("generatedReply").textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById("btnCopy");
        btn.textContent = "Copied!";
        setTimeout(() => btn.textContent = "Copy reply", 1500);
    });
}

// Close modal on overlay click
document.addEventListener("click", (e) => {
    if (e.target.id === "replyModal") closeReplyModal();
});

// Close modal on Escape
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeReplyModal();
});

// ── Utilities ───────────────────────────────────────────────────

async function toggleBookmark(postId, btn) {
    try {
        const resp = await fetch(`/api/bookmark/${postId}`, { method: "POST" });
        const data = await resp.json();
        btn.classList.toggle("bookmarked", data.bookmarked);
    } catch (err) {}
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
        const diffH = Math.floor((new Date() - d) / 3600000);
        if (diffH < 1) return Math.floor((new Date() - d) / 60000) + "m ago";
        if (diffH < 24) return diffH + "h ago";
        if (diffH < 168) return Math.floor(diffH / 24) + "d ago";
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    } catch { return isoStr; }
}

function esc(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
