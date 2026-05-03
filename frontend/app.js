/* Multi-page frontend for the FastAPI Blog Management System.
   Pages are served at /ui/*.html, assets at /static/*
   and API calls are same-origin.

   Polish features:
   - Role-based UI (admin/author/reader visibility)
   - Pagination for posts and comments
   - Owner/admin-only edit/delete on comments
   - Hide create/edit/delete post buttons from readers
*/

const API_BASE = "";
const TOKEN_KEY = "bms_token";

const POSTS_PER_PAGE = 5;
const COMMENTS_PER_PAGE = 10;

const state = {
  token: localStorage.getItem(TOKEN_KEY) || null,
  me: null,
  selectedPost: null,
  postsPage: 0,
  commentsPage: 0,
};

function el(id) {
  return document.getElementById(id);
}

function pageName() {
  return document.body?.dataset?.page || "";
}

function showAlert(message, type = "error") {
  const alerts = el("alerts");
  const alertText = el("alertText");
  if (!alerts || !alertText) return;
  alerts.hidden = false;
  alertText.textContent = message;
  alertText.className = `alert alert--${type}`;
}

function clearAlert() {
  const alerts = el("alerts");
  const alertText = el("alertText");
  if (!alerts || !alertText) return;
  alerts.hidden = true;
  alertText.textContent = "";
  alertText.className = "alert";
}

function setToken(token) {
  state.token = token;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
  renderAuth();
}

function authHeaders() {
  if (!state.token) return {};
  return { Authorization: `Bearer ${state.token}` };
}

async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.auth === true) Object.assign(headers, authHeaders());

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 204) return null;

  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const body = isJson ? await res.json().catch(() => null) : await res.text().catch(() => "");

  if (!res.ok) {
    const detail = body?.detail || body?.message || (typeof body === "string" ? body : "Request failed");
    throw new Error(`${res.status}: ${detail}`);
  }
  return body;
}

// ─── Role helpers ─────────────────────────────────────────────

function isAdmin() {
  return state.me?.role === "admin";
}

function isAuthor() {
  return state.me?.role === "author";
}

function isReader() {
  return state.me?.role === "reader";
}

function canCreatePost() {
  return isAdmin() || isAuthor();
}

function canEditPost(post) {
  if (!state.me) return false;
  if (isAdmin()) return true;
  return post.author_id === state.me.id;
}

function canEditComment(comment) {
  if (!state.me) return false;
  if (isAdmin()) return true;
  return comment.author_id === state.me.id;
}

function canDeleteComment(comment) {
  if (!state.me) return false;
  if (isAdmin()) return true;
  return comment.author_id === state.me.id;
}

// ─── Auth state rendering ─────────────────────────────────────

function renderAuth() {
  const authStatus = el("authStatus");
  const btnLogout = el("btnLogout");

  if (authStatus && btnLogout) {
    const username = state.me?.username;
    const role = state.me?.role;

    if (state.token && username) {
      authStatus.innerHTML = `Signed in as <strong>${safeText(username)}</strong> <span class="role-badge role-badge--${role}">${role}</span>`;
      btnLogout.hidden = false;
    } else if (state.token) {
      authStatus.textContent = "Signed in";
      btnLogout.hidden = false;
    } else {
      authStatus.textContent = "Not signed in";
      btnLogout.hidden = true;
    }
  }

  renderAuthVisibility();
}

function renderAuthVisibility() {
  const isAuthed = Boolean(state.token);
  const admin = isAdmin();
  const canCreate = canCreatePost();

  // Sections
  document.querySelectorAll("[data-auth='guest']").forEach((node) => {
    node.hidden = isAuthed;
  });
  document.querySelectorAll("[data-auth='authed']").forEach((node) => {
    node.hidden = !isAuthed;
  });

  // Navigation guests-only
  document.querySelectorAll(".nav__link--guest").forEach((node) => {
    node.style.display = isAuthed ? "none" : "";
  });

  // Admin-only elements
  document.querySelectorAll("[data-role='admin']").forEach((node) => {
    node.style.display = admin ? "" : "none";
  });

  // Author/Admin (anyone who can create posts)
  document.querySelectorAll("[data-role='creator']").forEach((node) => {
    node.style.display = canCreate ? "" : "none";
  });
}

function safeText(value) {
  if (value == null) return "";
  return String(value);
}

function formatDate(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return safeText(value);
  return d.toLocaleString();
}

function renderProfile() {
  const profile = el("profile");
  if (profile) {
    if (!state.me) {
      profile.classList.add("muted");
      profile.textContent = "(sign in to load /auth/me)";
    } else {
      profile.classList.remove("muted");
      profile.textContent = "";
      profile.appendChild(buildProfileCard(state.me));
    }
  }

  const profileCard = el("profileCard");
  if (!profileCard) return;
  profileCard.innerHTML = "";
  if (!state.me) {
    profileCard.classList.add("muted");
    profileCard.textContent = state.token ? "Loading profile…" : "(sign in to load /auth/me)";
    return;
  }
  profileCard.classList.remove("muted");
  profileCard.appendChild(buildProfileCard(state.me));
}

function buildProfileCard(me) {
  const wrap = document.createElement("div");
  wrap.className = "profileCard";

  const top = document.createElement("div");
  top.className = "profileCard__top";

  const left = document.createElement("div");
  const name = document.createElement("div");
  name.className = "profileCard__name";
  name.textContent = me.username ? safeText(me.username) : "User";

  const sub = document.createElement("div");
  sub.className = "profileCard__sub";
  const role = me.role ? safeText(me.role) : "";
  const id = me.id != null ? `#${safeText(me.id)}` : "";
  sub.textContent = [role && `Role: ${role}`, id && `User ${id}`].filter(Boolean).join(" · ");

  left.appendChild(name);
  left.appendChild(sub);

  const badge = document.createElement("div");
  badge.className = `role-badge role-badge--${me.role || "reader"}`;
  badge.textContent = me.role || "reader";

  top.appendChild(left);
  top.appendChild(badge);

  const dl = document.createElement("dl");
  dl.className = "kv";

  const addRow = (label, value) => {
    const row = document.createElement("div");
    row.className = "kv__row";
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value || "—";
    row.appendChild(dt);
    row.appendChild(dd);
    dl.appendChild(row);
  };

  addRow("Email", safeText(me.email));
  addRow("Status", (me.is_active === 1 || me.is_active === true) ? "Active" : "Inactive");
  addRow("Created", formatDate(me.created_at));
  addRow("Updated", formatDate(me.updated_at));

  wrap.appendChild(top);
  wrap.appendChild(dl);
  return wrap;
}

async function loadMe() {
  if (!state.token) {
    state.me = null;
    renderAuth();
    renderProfile();
    return;
  }

  try {
    state.me = await apiFetch("/auth/me", { auth: true });
  } catch {
    state.me = null;
    setToken(null);
  }
  renderAuth();
  renderProfile();
}

async function registerUser({ username, email, password }) {
  return apiFetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password }),
  });
}

async function loginUser({ username, password }) {
  const form = new URLSearchParams();
  form.set("username", username);
  form.set("password", password);

  const token = await apiFetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });

  setToken(token.access_token);
  await loadMe();
}

function getQueryInt(name) {
  const raw = new URLSearchParams(window.location.search).get(name);
  if (!raw) return null;
  const num = Number(raw);
  return Number.isFinite(num) ? num : null;
}

// ─── Pagination component ─────────────────────────────────────

function buildPagination(currentPage, hasNext, onChange) {
  const wrap = document.createElement("div");
  wrap.className = "pagination";

  const prev = document.createElement("button");
  prev.className = "btn btn--secondary";
  prev.type = "button";
  prev.textContent = "← Previous";
  prev.disabled = currentPage === 0;
  prev.addEventListener("click", () => onChange(currentPage - 1));

  const info = document.createElement("span");
  info.className = "pagination__info muted small";
  info.textContent = `Page ${currentPage + 1}`;

  const next = document.createElement("button");
  next.className = "btn btn--secondary";
  next.type = "button";
  next.textContent = "Next →";
  next.disabled = !hasNext;
  next.addEventListener("click", () => onChange(currentPage + 1));

  wrap.appendChild(prev);
  wrap.appendChild(info);
  wrap.appendChild(next);
  return wrap;
}

// ─── Posts ────────────────────────────────────────────────────

async function fetchPostsPage(page) {
  const skip = page * POSTS_PER_PAGE;
  // Fetch one extra to know if there's a next page
  const limit = POSTS_PER_PAGE + 1;
  const posts = await apiFetch(`/posts/?skip=${skip}&limit=${limit}`);
  const hasNext = posts.length > POSTS_PER_PAGE;
  const visible = hasNext ? posts.slice(0, POSTS_PER_PAGE) : posts;
  return { posts: visible, hasNext };
}

async function loadPostsIntoList(listEl, paginationEl, { mode } = { mode: "index" }) {
  if (!listEl) return;
  listEl.innerHTML = "";
  if (paginationEl) paginationEl.innerHTML = "";

  let result;
  try {
    result = await fetchPostsPage(state.postsPage);
  } catch (e) {
    showAlert(e.message);
    return;
  }

  const { posts, hasNext } = result;

  if (posts.length === 0) {
    const li = document.createElement("li");
    li.className = "list__item muted";
    li.textContent = state.postsPage === 0 ? "No posts yet." : "No more posts.";
    listEl.appendChild(li);
  } else {
    posts.forEach((post) => {
      listEl.appendChild(renderPostListItem(post, mode));
    });
  }

  if (paginationEl) {
    paginationEl.appendChild(
      buildPagination(state.postsPage, hasNext, async (newPage) => {
        state.postsPage = newPage;
        await loadPostsIntoList(listEl, paginationEl, { mode });
      })
    );
  }
}

function renderPostListItem(post, mode) {
  const li = document.createElement("li");
  li.className = "list__item";

  const title = document.createElement("h4");
  title.textContent = post.title;

  const meta = document.createElement("div");
  meta.className = "list__meta";
  meta.textContent = `Post #${post.id} · author_id=${post.author_id}`;

  const preview = document.createElement("div");
  preview.className = "list__preview";
  preview.textContent = (post.body || "").slice(0, 140) + (post.body?.length > 140 ? "…" : "");

  const actions = document.createElement("div");
  actions.className = "row row--actions";

  if (mode === "index") {
    const btn = document.createElement("button");
    btn.className = "btn btn--secondary";
    btn.type = "button";
    btn.textContent = "Select";
    btn.addEventListener("click", () => selectPostInline(post));
    actions.appendChild(btn);
  } else {
    const view = document.createElement("a");
    view.className = "btn btn--secondary";
    view.href = `/ui/post.html?id=${post.id}`;
    view.textContent = "View";
    actions.appendChild(view);

    if (canEditPost(post)) {
      const edit = document.createElement("a");
      edit.className = "btn btn--secondary";
      edit.href = `/ui/edit-post.html?id=${post.id}`;
      edit.textContent = "Edit";
      actions.appendChild(edit);
    }
  }

  li.appendChild(title);
  li.appendChild(meta);
  li.appendChild(preview);
  li.appendChild(actions);
  return li;
}

// ─── Comments ─────────────────────────────────────────────────

function flattenComments(tree) {
  const out = [];
  const visit = (c, depth) => {
    out.push({ ...c, _depth: depth });
    (c.replies || []).forEach((r) => visit(r, depth + 1));
  };
  (tree || []).forEach((c) => visit(c, 0));
  return out;
}

async function fetchCommentsPage(postId, page) {
  const skip = page * COMMENTS_PER_PAGE;
  const limit = COMMENTS_PER_PAGE + 1;
  const tree = await apiFetch(`/posts/${postId}/comments?skip=${skip}&limit=${limit}`, { auth: true });
  const hasNext = tree.length > COMMENTS_PER_PAGE;
  const visible = hasNext ? tree.slice(0, COMMENTS_PER_PAGE) : tree;
  return { tree: visible, hasNext };
}

async function loadComments(postId) {
  const list = el("commentsList");
  const paginationEl = el("commentsPagination");
  if (!list) return;

  list.innerHTML = "";
  if (paginationEl) paginationEl.innerHTML = "";

  let result;
  try {
    result = await fetchCommentsPage(postId, state.commentsPage);
  } catch (e) {
    showAlert(e.message);
    return;
  }

  const { tree, hasNext } = result;
  const comments = flattenComments(tree);

  if (comments.length === 0) {
    const li = document.createElement("li");
    li.className = "list__item muted";
    li.textContent = state.commentsPage === 0 ? "No comments yet. Be the first!" : "No more comments.";
    list.appendChild(li);
  } else {
    comments.forEach((c) => list.appendChild(commentItem(c, postId)));
  }

  if (paginationEl) {
    paginationEl.appendChild(
      buildPagination(state.commentsPage, hasNext, async (newPage) => {
        state.commentsPage = newPage;
        await loadComments(postId);
      })
    );
  }
}

async function addComment(postId, body) {
  await apiFetch(`/posts/${postId}/comments`, {
    method: "POST",
    auth: true,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
  });
  state.commentsPage = 0;
  await loadComments(postId);
}

async function replyToComment(commentId, body, postId) {
  await apiFetch(`/comments/${commentId}/reply`, {
    method: "POST",
    auth: true,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
  });
  await loadComments(postId);
}

async function updateComment(commentId, body, postId) {
  await apiFetch(`/comments/${commentId}`, {
    method: "PUT",
    auth: true,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
  });
  await loadComments(postId);
}

async function deleteComment(commentId, postId) {
  await apiFetch(`/comments/${commentId}`, {
    method: "DELETE",
    auth: true,
  });
  await loadComments(postId);
}

function commentItem(comment, postId) {
  const li = document.createElement("li");
  li.className = "list__item comment";
  li.style.marginLeft = `${(comment._depth || 0) * 20}px`;

  const meta = document.createElement("div");
  meta.className = "list__meta";
  const isOwner = state.me && comment.author_id === state.me.id;
  meta.innerHTML = `Comment #${comment.id} · author_id=${comment.author_id}${isOwner ? ' <span class="badge badge--mine">you</span>' : ''}${comment._depth > 0 ? ' <span class="badge">reply</span>' : ''}`;

  const body = document.createElement("div");
  body.className = "comment__body";
  body.textContent = comment.body;

  const actions = document.createElement("div");
  actions.className = "row row--actions";

  // Reply: any logged-in user can reply
  if (state.token) {
    const btnReply = document.createElement("button");
    btnReply.className = "btn btn--secondary btn--small";
    btnReply.type = "button";
    btnReply.textContent = "Reply";
    btnReply.addEventListener("click", async () => {
      const reply = prompt("Reply", "");
      if (reply == null || !reply.trim()) return;
      try {
        await replyToComment(comment.id, reply.trim(), postId);
      } catch (e) {
        showAlert(e.message);
      }
    });
    actions.appendChild(btnReply);
  }

  // Edit: only owner (or admin)
  if (canEditComment(comment)) {
    const btnEdit = document.createElement("button");
    btnEdit.className = "btn btn--secondary btn--small";
    btnEdit.type = "button";
    btnEdit.textContent = "Edit";
    btnEdit.addEventListener("click", async () => {
      const newBody = prompt("Edit comment", comment.body);
      if (newBody == null || !newBody.trim()) return;
      try {
        await updateComment(comment.id, newBody.trim(), postId);
      } catch (e) {
        showAlert(e.message);
      }
    });
    actions.appendChild(btnEdit);
  }

  // Delete: only owner (or admin)
  if (canDeleteComment(comment)) {
    const btnDelete = document.createElement("button");
    btnDelete.className = "btn btn--danger btn--small";
    btnDelete.type = "button";
    btnDelete.textContent = "Delete";
    btnDelete.addEventListener("click", async () => {
      if (!confirm("Delete this comment?")) return;
      try {
        await deleteComment(comment.id, postId);
      } catch (e) {
        showAlert(e.message);
      }
    });
    actions.appendChild(btnDelete);
  }

  li.appendChild(meta);
  li.appendChild(body);
  if (actions.children.length > 0) li.appendChild(actions);
  return li;
}

// ─── Post details renderer ────────────────────────────────────

function renderPostDetails(target, post) {
  if (!target) return;
  if (!post) {
    target.className = "panel muted";
    target.textContent = "Post not found.";
    return;
  }

  target.className = "panel";
  target.innerHTML = "";

  const h = document.createElement("h3");
  h.textContent = post.title;

  const meta = document.createElement("div");
  meta.className = "list__meta";
  meta.textContent = `Post #${post.id} · author_id=${post.author_id}`;

  const body = document.createElement("div");
  body.className = "post__body";
  body.textContent = post.body;

  target.appendChild(h);
  target.appendChild(meta);
  target.appendChild(body);
}

// ─── Post CRUD ────────────────────────────────────────────────

async function createPost(title, body) {
  return apiFetch("/posts/", {
    method: "POST",
    auth: true,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, body }),
  });
}

async function updatePost(postId, title, body) {
  return apiFetch(`/posts/${postId}`, {
    method: "PUT",
    auth: true,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, body }),
  });
}

async function deletePost(postId) {
  return apiFetch(`/posts/${postId}`, {
    method: "DELETE",
    auth: true,
  });
}

// ─── Index page inline post selection ─────────────────────────

async function selectPostInline(post) {
  state.selectedPost = post;
  state.commentsPage = 0;
  const postDetails = el("postDetails");
  renderPostDetails(postDetails, post);

  const commentsCard = el("commentsCard");
  if (commentsCard) commentsCard.hidden = false;

  const commentsHint = el("commentsHint");
  const formAddComment = el("formAddComment");

  if (!state.token) {
    if (commentsHint) commentsHint.textContent = "Login to read and add comments";
    if (formAddComment) formAddComment.hidden = true;
    return;
  }

  if (commentsHint) commentsHint.textContent = "";
  if (formAddComment) formAddComment.hidden = false;
  await loadComments(post.id);
}

// ─── Wiring ───────────────────────────────────────────────────

function wireCommon() {
  const btnLogout = el("btnLogout");
  if (btnLogout) {
    btnLogout.addEventListener("click", () => {
      setToken(null);
      state.me = null;
      renderAuth();
      renderProfile();
      // Reload to reset all state
      window.location.href = "/ui/";
    });
  }
}

function wireRegister() {
  const formRegister = el("formRegister");
  if (!formRegister) return;

  formRegister.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert();

    const fd = new FormData(formRegister);
    const payload = {
      username: String(fd.get("username") || "").trim(),
      email: String(fd.get("email") || "").trim(),
      password: String(fd.get("password") || ""),
    };

    try {
      const created = await registerUser(payload);
      showAlert(`Welcome, ${created.username}! Account created. Please log in.`, "success");
      formRegister.reset();
    } catch (err) {
      showAlert(err.message);
    }
  });
}

function wireLogin() {
  const formLogin = el("formLogin");
  if (!formLogin) return;

  formLogin.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert();

    const fd = new FormData(formLogin);
    const payload = {
      username: String(fd.get("username") || "").trim(),
      password: String(fd.get("password") || ""),
    };

    try {
      await loginUser(payload);
      // Reload so visibility rules apply everywhere
      const target = pageName() === "login" ? "/ui/posts.html" : window.location.pathname;
      window.location.href = target;
    } catch (err) {
      showAlert(err.message);
    }
  });
}

function wirePostsPage() {
  if (pageName() !== "posts") return;
  const btnRefreshPosts = el("btnRefreshPosts");
  const postsList = el("postsList");
  const postsPagination = el("postsPagination");
  if (!postsList) return;

  if (btnRefreshPosts) {
    btnRefreshPosts.addEventListener("click", async () => {
      try {
        clearAlert();
        state.postsPage = 0;
        await loadPostsIntoList(postsList, postsPagination, { mode: "list" });
      } catch (e) {
        showAlert(e.message);
      }
    });
  }
}

function wireCreatePost() {
  const form = el("formCreatePost");
  if (!form) return;

  // Guard: only authors/admins should reach here
  if (!canCreatePost()) {
    showAlert("Only authors and admins can create posts.");
    form.hidden = true;
    return;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert();

    const fd = new FormData(form);
    const title = String(fd.get("title") || "").trim();
    const body = String(fd.get("body") || "").trim();

    try {
      const created = await createPost(title, body);
      window.location.href = `/ui/post.html?id=${created.id}`;
    } catch (err) {
      showAlert(err.message);
    }
  });
}

async function initEditPostPage() {
  const form = el("formEditPost");
  const btnDelete = el("btnDeletePost");
  const linkViewPost = el("linkViewPost");
  const titleEl = el("editTitle");
  const bodyEl = el("editBody");
  if (!form || !btnDelete || !linkViewPost || !titleEl || !bodyEl) return;

  const postId = getQueryInt("id");
  if (!postId) {
    showAlert("Missing post id (?id=...)");
    return;
  }

  linkViewPost.href = `/ui/post.html?id=${postId}`;

  let post;
  try {
    post = await apiFetch(`/posts/${postId}`);
    titleEl.value = post.title;
    bodyEl.value = post.body;
  } catch (e) {
    showAlert(e.message);
    return;
  }

  // Guard: only owner or admin can edit
  if (!canEditPost(post)) {
    showAlert("You don't have permission to edit this post.");
    form.hidden = true;
    return;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert();
    try {
      await updatePost(postId, titleEl.value.trim(), bodyEl.value.trim());
      showAlert("Saved.", "success");
    } catch (err) {
      showAlert(err.message);
    }
  });

  btnDelete.addEventListener("click", async () => {
    if (!confirm("Delete this post? This cannot be undone.")) return;
    clearAlert();
    try {
      await deletePost(postId);
      window.location.href = "/ui/posts.html";
    } catch (err) {
      showAlert(err.message);
    }
  });
}

async function initPostPage() {
  const postId = getQueryInt("id");
  const postDetails = el("postDetails");
  const formAddComment = el("formAddComment");
  const commentsHint = el("commentsHint");
  const linkEditPost = el("linkEditPost");

  if (!postId || !postDetails) return;

  let post;
  try {
    post = await apiFetch(`/posts/${postId}`);
    renderPostDetails(postDetails, post);
  } catch (e) {
    renderPostDetails(postDetails, null);
    showAlert(e.message);
    return;
  }

  // Show edit link only if user can edit
  if (linkEditPost) {
    if (canEditPost(post)) {
      linkEditPost.href = `/ui/edit-post.html?id=${postId}`;
      linkEditPost.hidden = false;
    } else {
      linkEditPost.hidden = true;
    }
  }

  if (!state.token) {
    if (commentsHint) commentsHint.textContent = "Login to read and post comments";
    if (formAddComment) formAddComment.hidden = true;
    return;
  }

  if (commentsHint) commentsHint.textContent = "";
  if (formAddComment) {
    formAddComment.hidden = false;
    formAddComment.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearAlert();
      const fd = new FormData(formAddComment);
      const body = String(fd.get("body") || "").trim();
      if (!body) return;
      try {
        await addComment(postId, body);
        formAddComment.reset();
      } catch (err) {
        showAlert(err.message);
      }
    });
  }

  try {
    await loadComments(postId);
  } catch (e) {
    showAlert(e.message);
  }
}

function wireUsersPage() {
  if (pageName() !== "users") return;

  const btn = el("btnLoadUsers");
  const out = el("usersOutput");
  const accessGuard = el("usersAccessGuard");
  if (!btn || !out) return;

  // Guard: only admins can see this page properly
  if (!isAdmin()) {
    if (accessGuard) accessGuard.hidden = false;
    btn.disabled = true;
    out.textContent = "Admin access required.";
    return;
  }

  if (accessGuard) accessGuard.hidden = true;

  btn.addEventListener("click", async () => {
    clearAlert();
    try {
      const users = await apiFetch("/auth/users", { auth: true });
      out.classList.remove("muted");
      out.innerHTML = "";
      out.appendChild(renderUsersTable(users));
    } catch (e) {
      out.classList.add("muted");
      out.textContent = "(failed to load)";
      showAlert(e.message);
    }
  });
}

function renderUsersTable(users) {
  const wrap = document.createElement("div");
  wrap.className = "users-table";

  if (!users || users.length === 0) {
    wrap.textContent = "No users found.";
    return wrap;
  }

  const table = document.createElement("table");
  table.className = "data-table";

  const thead = document.createElement("thead");
  thead.innerHTML = `
    <tr>
      <th>ID</th>
      <th>Username</th>
      <th>Email</th>
      <th>Role</th>
      <th>Status</th>
      <th>Created</th>
    </tr>
  `;
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  users.forEach((u) => {
    const tr = document.createElement("tr");
    const active = u.is_active === 1 || u.is_active === true;
    tr.innerHTML = `
      <td>${safeText(u.id)}</td>
      <td>${safeText(u.username)}</td>
      <td>${safeText(u.email)}</td>
      <td><span class="role-badge role-badge--${u.role}">${safeText(u.role)}</span></td>
      <td>${active ? '<span class="badge badge--ok">Active</span>' : '<span class="badge badge--off">Inactive</span>'}</td>
      <td class="muted small">${formatDate(u.created_at)}</td>
    `;
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  wrap.appendChild(table);
  return wrap;
}

async function initIndexPage() {
  const postsList = el("postsList");
  const postsPagination = el("postsPagination");
  const btnRefreshPosts = el("btnRefreshPosts");
  const postDetails = el("postDetails");
  const commentsCard = el("commentsCard");
  const formAddComment = el("formAddComment");

  if (!postsList || !postDetails) return;

  if (commentsCard) commentsCard.hidden = true;
  if (formAddComment) formAddComment.hidden = true;

  if (btnRefreshPosts) {
    btnRefreshPosts.addEventListener("click", async () => {
      clearAlert();
      state.postsPage = 0;
      try {
        await loadPostsIntoList(postsList, postsPagination, { mode: "index" });
      } catch (e) {
        showAlert(e.message);
      }
    });
  }

  if (formAddComment) {
    formAddComment.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearAlert();
      if (!state.selectedPost) return;
      const fd = new FormData(formAddComment);
      const body = String(fd.get("body") || "").trim();
      if (!body) return;
      try {
        await addComment(state.selectedPost.id, body);
        formAddComment.reset();
      } catch (err) {
        showAlert(err.message);
      }
    });
  }

  await loadPostsIntoList(postsList, postsPagination, { mode: "index" });
}

// ─── Boot ─────────────────────────────────────────────────────

(async function init() {
  wireCommon();
  await loadMe();

  wireRegister();
  wireLogin();
  wirePostsPage();
  wireCreatePost();
  wireUsersPage();

  const p = pageName();
  try {
    if (p === "index") await initIndexPage();
    if (p === "post") await initPostPage();
    if (p === "edit-post") await initEditPostPage();
    if (p === "posts") {
      const postsList = el("postsList");
      const postsPagination = el("postsPagination");
      if (postsList) await loadPostsIntoList(postsList, postsPagination, { mode: "list" });
    }
  } catch (e) {
    showAlert(e.message);
  }
})();
