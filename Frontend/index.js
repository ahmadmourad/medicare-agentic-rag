import {clinicsArray} from './data.js'

const clinicsGrid = document.getElementById("clinics-grid")


function renderClinics() {
    const clinicsItemsHtml = clinicsArray.map(clinicObj =>
        `<div class="clinic-item">
            <h3>${clinicObj.name}</h3>
            <p>${clinicObj.description}</p>
            <button data-book="${clinicObj.id}">Book Appointment</button>
        </div>`
    ).join('')

    clinicsGrid.innerHTML = clinicsItemsHtml
}

renderClinics()