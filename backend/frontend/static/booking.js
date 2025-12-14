const durations = { 'reinigung1': 60, 'reinigung2': 90, 'reinigung3': 120 };
const workStart = 7.5 * 60; // 7:30
const workEnd = 18 * 60;    // 18:00

const serviceSelect = document.getElementById('service');
const dateInput = document.getElementById('date');
const timeSlotsDiv = document.getElementById('timeSlots');
const form = document.getElementById('bookingForm');
const messageDiv = document.getElementById('message');

let busySlots = [];
let selectedSlot = null;

// ==================== HELPERS ====================
async function fetchBusySlots() {
  try {
    const res = await fetch('/api/slots');
    const data = await res.json();
    busySlots = data.map(b => ({
      start_time: new Date(b.start_time),
      end_time: new Date(b.end_time)
    }));
  } catch (err) {
    console.error('Fehler beim Laden der Slots:', err);
  }
}

function parseDateInput(value) {
  if (!value) return null;
  const [year, month, day] = value.split('-').map(Number);
  return new Date(year, month - 1, day);
}

function getAllSlots() {
  const slots = [];
  for (let t = Math.floor(workStart); t < workEnd; t += 30) slots.push(t);
  return slots;
}

function toLocalISOString(d) {
  const pad = n => n.toString().padStart(2,'0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// ==================== MAIN ====================
async function populateSlots() {
  await fetchBusySlots();
  const service = serviceSelect.value;
  const serviceDuration = durations[service];

  const date = parseDateInput(dateInput.value);
  if (!date || isNaN(date.getTime())) {
    timeSlotsDiv.innerHTML = '';
    return;
  }

  const allSlots = getAllSlots();
  timeSlotsDiv.innerHTML = '';

  allSlots.forEach(minutes => {
    const slotStart = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    slotStart.setHours(Math.floor(minutes / 60), minutes % 60, 0, 0);
    const slotEnd = new Date(slotStart.getTime() + 30*60000); // каждый слот = 30 мин

    const slotDiv = document.createElement('div');
    slotDiv.textContent = `${slotStart.getHours().toString().padStart(2,'0')}:${slotStart.getMinutes().toString().padStart(2,'0')}`;
    slotDiv.dataset.minutes = minutes;

    // ================= проверка занятости =================
    let busy = false;
    const now = new Date();
    if (slotEnd <= now || minutes < workStart || minutes >= workEnd) busy = true;
    for (const b of busySlots) {
      if (slotStart < b.end_time && slotEnd > b.start_time) {
        busy = true;
        break;
      }
    }

    if (busy) {
      slotDiv.className = 'slot busy';
    } else {
      slotDiv.className = 'slot free';
      slotDiv.addEventListener('click', () => {
        document.querySelectorAll('.slot').forEach(s => s.classList.remove('selected'));

        const clickedMinutes = parseInt(slotDiv.dataset.minutes);
        const slotsToHighlight = Math.ceil(serviceDuration / 30);

        for (let i = 0; i < slotsToHighlight; i++) {
          const m = clickedMinutes + i*30;
          const s = document.querySelector(`.slot[data-minutes='${m}']`);
          if (s && s.classList.contains('free')) s.classList.add('selected');
        }

        selectedSlot = clickedMinutes;
      });
    }

    // подсветка выбранного слота после перерисовки
    if (selectedSlot !== null) {
      const slotsToHighlight = Math.ceil(serviceDuration / 30);
      if (minutes >= selectedSlot && minutes < selectedSlot + slotsToHighlight*30) {
        slotDiv.classList.add('selected');
      }
    }

    timeSlotsDiv.appendChild(slotDiv);
  });
}

// ==================== EVENT LISTENERS ====================
dateInput.addEventListener('change', () => {
  const date = parseDateInput(dateInput.value);
  if (!date) return;
  if (date.getDay() === 0 || date.getDay() === 6) {
    alert('Nur Werktage (Montag-Freitag) sind erlaubt.');
    dateInput.value = '';
    timeSlotsDiv.innerHTML = '';
  } else {
    populateSlots();
  }
});

serviceSelect.addEventListener('change', populateSlots);
window.addEventListener('load', populateSlots);

// ==================== FORM SUBMIT ====================
form.addEventListener('submit', async e => {
  e.preventDefault();
  if (selectedSlot === null) {
    alert('Bitte wählen Sie eine Uhrzeit.');
    return;
  }

  const date = parseDateInput(dateInput.value);
  const service = serviceSelect.value;
  const serviceDuration = durations[service];
  date.setHours(Math.floor(selectedSlot / 60), selectedSlot % 60, 0, 0);

  const data = {
    name: document.getElementById('name').value,
    phone: document.getElementById('phone').value,
    email: document.getElementById('email').value,
    service: service,
    start_time: toLocalISOString(date)
  };

  try {
    const res = await fetch('/api/book', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    const result = await res.json();

    if (res.ok) {
      busySlots.push({ start_time: date, end_time: new Date(date.getTime() + serviceDuration*60000) });
      messageDiv.innerHTML = `<div class="alert alert-success">
        Vielen Dank! Ihre Buchung für ${date.toLocaleDateString()} um ${date.getHours().toString().padStart(2,'0')}:${date.getMinutes().toString().padStart(2,'0')} wurde erfolgreich erstellt.
      </div>`;
      selectedSlot = null;
      populateSlots();
    } else {
      messageDiv.innerHTML = `<div class="alert alert-danger">${result.detail}</div>`;
    }
  } catch (err) {
    messageDiv.innerHTML = `<div class="alert alert-danger">Fehler: ${err}</div>`;
  }
});
