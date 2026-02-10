// ================= CONFIG =================
const WORK_START = 7.5 * 60; // 07:30
const WORK_END = 18 * 60;    // 18:00
const SLOT_STEP = 30;        // minutes

// ================= DOM =================
const serviceInput = document.getElementById('service'); // hidden input
const servicesContainer = document.getElementById('services');
const dateInput = document.getElementById('date');
const timeSlotsDiv = document.getElementById('timeSlots');
const form = document.getElementById('bookingForm');
const messageDiv = document.getElementById('message');

// ================= STATE =================
let services = {};
let busySlots = [];
let selectedStartMinutes = null;
let selectedService = null;

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

// ================= API =================
// Глобальная функция для загрузки занятых слотов
window.loadBusySlots = async function() {
    busySlots = [];
    if (!dateInput.value) return;

    try {
        const res = await fetch(`/api/slots?date=${dateInput.value}`);
        if (!res.ok) return;
        const data = await res.json();
        busySlots = data.map(b => ({
            start: new Date(b.start_time),
            end: new Date(b.end_time)
        }));
    } catch (err) {
        console.error('loadBusySlots error:', err);
    }
};

// Отрисовка слотов
async function renderSlots() {
    await window.loadBusySlots();
    clearSelection();

    const date = parseDate(dateInput.value);
    if (!date) {
        timeSlotsDiv.innerHTML = '';
        return;
    }

    if (!selectedService) {
        timeSlotsDiv.innerHTML = '<div class="text-muted">Bitte zuerst einen Service wählen</div>';
        return;
    }

    const service = services[selectedService];
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

async function loadServices() {
    try {
        const res = await fetch('/api/services');
        services = await res.json();

        servicesContainer.innerHTML = '';

        for (const key in services) {
            const s = services[key];

            const card = document.createElement('div');
            card.className = 'service-card';
            card.dataset.key = key;

            card.innerHTML = `
                <div class="service-header d-flex justify-content-between align-items-center">
                    <div class="service-title fw-bold">${s.name}</div>
                    <div class="service-meta text-muted">${s.duration} Min · €${s.price}</div>
                </div>
                <p class="description mt-2 mb-1">${s.description}</p>
                <button type="button" class="btn btn-link btn-sm toggle-desc">Mehr anzeigen</button>
            `;

            servicesContainer.appendChild(card);

            // ====================== Работа с кнопкой ======================
            const desc = card.querySelector('p.description');
            const toggleBtn = card.querySelector('.toggle-desc');

            // Скрываем кнопку, если текст помещается полностью
            if (desc.scrollHeight <= desc.clientHeight) {
                toggleBtn.style.display = 'none';
            }

            // Кнопка "Mehr anzeigen"
            toggleBtn.addEventListener('click', e => {
                e.stopPropagation(); // чтобы клик по кнопке не выбирал сервис
                desc.classList.toggle('expanded');
                toggleBtn.textContent = desc.classList.contains('expanded') ? 'Weniger anzeigen' : 'Mehr anzeigen';
            });

            // ====================== Выбор карточки ======================
            card.addEventListener('click', () => {
                document.querySelectorAll('.service-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                selectedService = key;
                serviceInput.value = key;
                renderSlots();
            });
        }
    } catch (err) {
        console.error('Ошибка при загрузке сервисов:', err);
        servicesContainer.innerHTML = '<div class="text-danger">Fehler beim Laden der Services</div>';
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

window.addEventListener('DOMContentLoaded', async () => {
    await loadServices();
    renderSlots();
});

// ================= SUBMIT =================
form.addEventListener('submit', async e => {
    e.preventDefault();

    if (!selectedService) {
        alert('Bitte Service auswählen');
        return;
    }

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
        service: selectedService,
        start_time: toLocalISOString(date)
    };

    const res = await fetch('/api/book', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (res.ok) {
        const serviceName = services[selectedService].name;
        const params = new URLSearchParams({
            date: dateInput.value,
            time: `${pad(date.getHours())}:${pad(date.getMinutes())}`,
            service: serviceName
        });
        window.location.href = '/success?' + params.toString();
    }
});