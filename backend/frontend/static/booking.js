// ================= CONFIG =================
const WORK_START = 7.5 * 60; // 07:30
const WORK_END = 18 * 60;   // 18:00
const SLOT_STEP = 30;       // minutes

// ================= DOM =================
const serviceSelect = document.getElementById('service');
const dateInput = document.getElementById('date');
const timeSlotsDiv = document.getElementById('timeSlots');
const form = document.getElementById('bookingForm');
const messageDiv = document.getElementById('message');

// ================= STATE =================
let services = {};
let busySlots = [];
let selectedStartMinutes = null;

// ================= HELPERS =================
function pad(n) {
  return n.toString().padStart(2, '0');
}

function parseDate(value) {
  if (!value) return null;
  const [y, m, d] = value.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function toLocalISOString(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function getAllSlotMinutes() {
  const slots = [];
  for (let m = Math.floor(WORK_START); m < WORK_END; m += SLOT_STEP) {
    slots.push(m);
  }
  return slots;
}

// ================= API =================
async function loadServices() {
  const res = await fetch('/api/services');
  services = await res.json();

  serviceSelect.innerHTML = '';
  for (const key in services) {
    const s = services[key];
    const opt = document.createElement('option');
    opt.value = key;
    opt.textContent = `${s.name} – ${s.duration} Min – €${s.price}`;
    opt.title = s.description;
    serviceSelect.appendChild(opt);
  }
}

async function loadBusySlots() {
  const res = await fetch('/api/slots');
  const data = await res.json();
  busySlots = data.map(b => ({
    start: new Date(b.start_time),
    end: new Date(b.end_time)
  }));
}

// ================= LOGIC =================
function isRangeFree(start, end) {
  for (const b of busySlots) {
    if (start < b.end && end > b.start) return false;
  }
  return true;
}

function clearSelection() {
  selectedStartMinutes = null;
  document.querySelectorAll('.slot').forEach(s => s.classList.remove('selected'));
}

async function renderSlots() {
  await loadBusySlots();
  clearSelection();

  const date = parseDate(dateInput.value);
  if (!date) {
    timeSlotsDiv.innerHTML = '';
    return;
  }

  const serviceKey = serviceSelect.value;
  const service = services[serviceKey];
  const duration = service.duration;

  timeSlotsDiv.innerHTML = '';

  for (const minutes of getAllSlotMinutes()) {
    const slotStart = new Date(date);
    slotStart.setHours(Math.floor(minutes / 60), minutes % 60, 0, 0);

    const slotEnd = new Date(slotStart.getTime() + duration * 60000);

    const div = document.createElement('div');
    div.classList.add('slot');
    div.dataset.minutes = minutes;
    div.textContent = `${pad(slotStart.getHours())}:${pad(slotStart.getMinutes())}`;

    let busy = false;

    if (slotEnd.getTime() > new Date(date).setHours(18, 0, 0, 0)) busy = true;
    if (slotEnd <= new Date()) busy = true;
    if (!isRangeFree(slotStart, slotEnd)) busy = true;

    if (busy) {
      div.classList.add('busy');
    } else {
      div.classList.add('free');
      div.addEventListener('click', () => {
        clearSelection();
        selectedStartMinutes = minutes;

        const blocks = Math.ceil(duration / SLOT_STEP);
        for (let i = 0; i < blocks; i++) {
          const m = minutes + i * SLOT_STEP;
          const el = document.querySelector(`.slot[data-minutes='${m}']`);
          if (el) el.classList.add('selected');
        }
      });
    }

    timeSlotsDiv.appendChild(div);
  }
}

// ================= EVENTS =================
dateInput.addEventListener('change', () => {
  const d = parseDate(dateInput.value);
  if (!d) return;
  if (d.getDay() === 0 || d.getDay() === 6) {
    alert('Nur Werktage (Mo–Fr) erlaubt');
    dateInput.value = '';
    timeSlotsDiv.innerHTML = '';
    return;
  }
  renderSlots();
});

serviceSelect.addEventListener('change', renderSlots);

window.addEventListener('load', async () => {
  await loadServices();
  renderSlots();
});

// ================= SUBMIT =================
form.addEventListener('submit', async e => {
  e.preventDefault();

  if (selectedStartMinutes === null) {
    alert('Bitte Uhrzeit wählen');
    return;
  }

  const date = parseDate(dateInput.value);
  date.setHours(Math.floor(selectedStartMinutes / 60), selectedStartMinutes % 60, 0, 0);

  const payload = {
    name: document.getElementById('name').value,
    phone: document.getElementById('phone').value,
    email: document.getElementById('email').value,
    service: serviceSelect.value,
    start_time: toLocalISOString(date)
  };

  const res = await fetch('/api/book', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (res.ok) {
      const serviceKey = serviceSelect.value;
      const serviceName = services[serviceKey].name; // получаем читаемое название

      const params = new URLSearchParams({
          date: dateInput.value,
          time: `${pad(date.getHours())}:${pad(date.getMinutes())}`,
          service: serviceName
      });

      window.location.href = '/success?' + params.toString();
  }

});