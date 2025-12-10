import { clinicsArray } from './data.js'

const clinicsGrid = document.getElementById("clinics-grid")
const clinicBookingForm = document.getElementById("booking-clinic-modal")
const bookingDoneMsg = document.getElementById('booking-msg')

function renderClinics() {
    const clinicsItemsHtml = clinicsArray.map(clinicObj =>
        `<div class="clinic-item">
            <h3>${clinicObj.name}</h3>
            <p>${clinicObj.description}</p>
            <button data-book="${clinicObj.name}">Book Appointment</button>
        </div>`
    ).join('')

    clinicsGrid.innerHTML = clinicsItemsHtml
}

renderClinics()


document.addEventListener('click', handleButtonClicks)

function handleButtonClicks(e) {
    
    console.log(e.target.dataset)
    if (e.target.dataset.book) {
        document.getElementById('clinic-name-field').value = e.target.dataset.book
        clinicBookingForm.style.display = 'flex'
        document.getElementById('patient-name-field').focus()
        document.body.style.pointerEvents = 'none'
        clinicBookingForm.style.pointerEvents = 'auto'
    }

    if (e.target.dataset.closeformbtn) {
        clinicBookingForm.style.display = 'none'
        document.body.style.pointerEvents = 'auto'
    }

    if (!e.target.dataset.book && !clinicBookingForm.contains(e.target)) {
        clinicBookingForm.style.display = 'none'
        document.body.style.pointerEvents = 'auto'
    }

    if (e.target.dataset.closemsgbtn) {
        bookingDoneMsg.style.display = 'none'
    }

}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        clinicBookingForm.style.display = 'none'
        document.body.style.pointerEvents = 'auto'
    }
});


clinicBookingForm.addEventListener('submit', handleFormData)

function handleFormData(e) {
    e.preventDefault()

    const clinicName = document.getElementById('clinic-name-field').value
    const patientName = document.getElementById('patient-name-field').value
    const appointmentDate = document.getElementById('date-field').value
    const appointmentTime = document.getElementById('time-field').value
    const bookingDoneMsg = document.getElementById("booking-msg")

    bookingDoneMsg.style.display = 'block'

    bookingDoneMsg.innerHTML += `Thank you,  <strong>${patientName}!</strong> Your appointment for <strong>${clinicName}</strong> on <strong>${appointmentDate}<strong/> at <strong>${appointmentTime}</strong> has been booked.`

    clinicBookingForm.reset()
    clinicBookingForm.style.display = 'none'
    document.body.style.pointerEvents = 'auto';
}


