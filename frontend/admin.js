async function login() {
  const res = await fetch('/admin/login', {
    method: 'POST',
    body: new URLSearchParams({
      user: document.getElementById('user').value,
      password: document.getElementById('pass').value
    })
  });

  if (res.ok) load();
  else alert("Login falsch");
}

async function load() {
  const res = await fetch('/api/admin/bookings');
  const data = await res.json();

  const div = document.getElementById('list');
  div.innerHTML = '';

  data.forEach(b => {
    const el = document.createElement('div');
    el.className = 'border p-2 mb-2';
    el.innerHTML = `
      <b>${b.name}</b> – ${new Date(b.start).toLocaleString()}
      (${b.status})
      ${b.status === 'confirmed'
        ? `<button onclick="cancel(${b.id})">X</button>`
        : ''}
    `;
    div.appendChild(el);
  });
}

async function cancel(id) {
  await fetch('/api/admin/cancel/' + id, { method: 'POST' });
  load();
}
