const $ = (id) => document.getElementById(id);
const state = { cuisines: new Set(), liked: new Set(JSON.parse(localStorage.getItem("liked") || "[]")), coords: null };

async function init() {
  const r = await fetch("/api/options");
  const { cuisines } = await r.json();
  const box = $("cuisines");
  cuisines.forEach((c) => {
    const el = document.createElement("span");
    el.className = "chip";
    el.textContent = c;
    el.onclick = () => {
      state.cuisines.has(c) ? state.cuisines.delete(c) : state.cuisines.add(c);
      el.classList.toggle("on");
    };
    box.appendChild(el);
  });
}

function getCoords() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lon: p.coords.longitude }),
      () => resolve(null),
      { timeout: 4000 }
    );
  });
}

async function recommend() {
  const btn = $("go");
  btn.disabled = true;
  $("status").textContent = "Finding meals…";
  let geo = {};
  if ($("geo").checked) geo = (await getCoords()) || {};
  const body = {
    cuisines: [...state.cuisines],
    diet: $("diet").value,
    gluten_free: $("gf").checked,
    spice: $("spice").value === "" ? null : Number($("spice").value),
    max_price: $("price").value ? Number($("price").value) : null,
    weather: $("weather").value || null,
    location: $("loc").value.trim() || null,
    hour: new Date().getHours(),
    liked_ids: [...state.liked],
    ...geo,
  };
  try {
    const r = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await r.json();
    render(data);
  } catch (e) {
    $("status").textContent = "Something went wrong. Try again.";
  } finally {
    btn.disabled = false;
  }
}

function render({ results, weather, hour, nearby }) {
  const out = $("results");
  out.innerHTML = "";
  if (!results.length) {
    $("status").textContent = "No matches. Loosen a filter.";
    return;
  }
  $("status").textContent = `Top ${results.length} picks` + (weather ? ` · weather: ${weather}` : "") + ` · hour: ${hour}`
    + (nearby && nearby.length ? ` · nearby: ${nearby.slice(0, 5).map((n) => n.name).join(", ")}` : "");
  results.forEach((m) => {
    const c = document.createElement("div");
    c.className = "card";
    c.innerHTML = `
      <h3>${m.name}</h3>
      <div class="rest">${m.restaurant} · ${m.cuisine}</div>
      <div class="tags">
        <span class="tag">${m.diet}</span>
        <span class="tag">spice: ${m.spice}</span>
        ${m.gluten_free ? '<span class="tag">gluten-free</span>' : ""}
      </div>
      <div class="why">${m.why}</div>
      <div class="meta">
        <span>₹${m.price} · ★${m.rating} · ${m.delivery_min} min</span>
        <button class="like ${state.liked.has(m.id) ? "on" : ""}" data-id="${m.id}">♥</button>
      </div>`;
    c.querySelector(".like").onclick = (e) => {
      const id = m.id;
      state.liked.has(id) ? state.liked.delete(id) : state.liked.add(id);
      e.target.classList.toggle("on");
      localStorage.setItem("liked", JSON.stringify([...state.liked]));
    };
    out.appendChild(c);
  });
}

$("go").onclick = recommend;
init();
