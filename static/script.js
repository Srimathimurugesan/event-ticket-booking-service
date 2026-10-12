
const API_URL = "/api";

// ------------------------------
// Common API function
// ------------------------------

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            ...(options.body ? { "Content-Type": "application/json" } : {}),
            ...(options.headers || {})
        }
    });

    const text = await response.text();

    let data;

    try {
        data = text ? JSON.parse(text) : {};
    } catch {
        data = { message: text || "Unexpected server response" };
    }

    if (!response.ok) {
        const error = new Error(
            data.detail
                ? JSON.stringify(data.detail)
                : data.message || data.error || "Request failed"
        );

        error.status = response.status;
        throw error;
    }

    return data;
}

// ------------------------------
// Common display functions
// ------------------------------

function formatLabel(key) {
    const labels = {
        id: "ID",
        event_id: "Event ID",
        event_name: "Event Name",
        customer_name: "Customer Name",
        customer_email: "Customer Email",
        event_date: "Event Date",
        total_seats: "Total Seats",
        seats_sold: "Seats Sold",
        available_seats: "Available Seats",
        total_revenue: "Total Revenue",
        occupancy_pct: "Occupancy",
        demand_band: "Demand Level",
        base_price: "Base Price",
        price_per_seat: "Price Per Seat",
        total_amount: "Total Amount",
        seat_numbers: "Seat Numbers",
        rejection_reason: "Rejection Reason",
        booked_on: "Booking Date",
        created_at: "Created At"
    };

    return labels[key] || key
        .replace(/_/g, " ")
        .replace(/\b\w/g, letter => letter.toUpperCase());
}

function formatValue(key, value) {
    if (value === null || value === undefined || value === "") {
        return "—";
    }

    if (key === "seat_numbers" && typeof value === "string") {
        try {
            const parsed = JSON.parse(value);

            if (Array.isArray(parsed)) {
                return parsed.join(", ");
            }
        } catch {
            // Display the original value if it is not JSON.
        }
    }

    if (Array.isArray(value)) {
        return value.length ? value.join(", ") : "None";
    }

    if (typeof value === "object") {
        return JSON.stringify(value);
    }

    if (key === "total_revenue" ||
        key === "total_amount" ||
        key === "base_price" ||
        key === "price_per_seat") {
        return `₹${Number(value).toLocaleString("en-IN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })}`;
    }

    if (key === "occupancy_pct") {
        return `${value}%`;
    }

    if (key === "demand_band") {
        return String(value).toUpperCase();
    }

    return String(value);
}

function createElement(tag, text, styles = {}) {
    const element = document.createElement(tag);

    if (text !== undefined && text !== null) {
        element.textContent = String(text);
    }

    Object.assign(element.style, styles);

    return element;
}

function showMessage(elementId, message, success = false) {
    const container = document.getElementById(elementId);

    container.replaceChildren();

    const box = createElement("div", message, {
        padding: "14px",
        marginTop: "12px",
        borderRadius: "8px",
        background: success ? "#e8f7ee" : "#fff0f0",
        color: success ? "#176b38" : "#a12626",
        border: `1px solid ${success ? "#a6dfba" : "#f0b4b4"}`,
        overflowWrap: "anywhere"
    });

    container.appendChild(box);
}

function createCard(title, data, options = {}) {
    const card = createElement("div", undefined, {
        background: options.background || "#ffffff",
        border: `1px solid ${options.borderColor || "#e0e0ee"}`,
        borderRadius: "10px",
        padding: "18px",
        marginTop: "14px",
        boxShadow: "0 3px 10px rgba(0,0,0,0.04)",
        overflowWrap: "anywhere"
    });

    card.appendChild(createElement("h3", title, {
        marginTop: "0",
        marginBottom: "14px",
        color: options.titleColor || "#29245c"
    }));

    return card;
}

function addField(card, label, value) {
    const row = createElement("div", undefined, {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: "16px",
        padding: "9px 0",
        borderBottom: "1px solid #eeeeF5"
    });

    row.appendChild(createElement("span", label, {
        color: "#66667a",
        flex: "1"
    }));

    row.appendChild(createElement("strong", value, {
        color: "#252541",
        flex: "1",
        textAlign: "right",
        overflowWrap: "anywhere"
    }));

    card.appendChild(row);
}

function renderObjectCard(container, title, data, options = {}) {
    const card = createCard(title, data, options);

    for (const [key, value] of Object.entries(data)) {
        if (key === "rejection_reason" && !value) {
            continue;
        }

        addField(card, formatLabel(key), formatValue(key, value));
    }

    container.appendChild(card);
}

function showObject(elementId, title, data, options = {}) {
    const container = document.getElementById(elementId);

    container.replaceChildren();

    if (!data || typeof data !== "object" || Array.isArray(data)) {
        showMessage(elementId, "No details were found.");
        return;
    }

    renderObjectCard(container, title, data, options);
}

function showError(elementId, error) {
    const message = error.status
        ? `Request failed (${error.status}): ${error.message}`
        : `Unable to complete the request: ${error.message}`;

    showMessage(elementId, message);
}

// ------------------------------
// 1. Create an event
// ------------------------------

document.getElementById("eventForm").addEventListener(
    "submit",
    async event => {
        event.preventDefault();

        const eventData = {
            name: document.getElementById("eventName").value.trim(),
            venue: document.getElementById("venue").value.trim(),
            category: document.getElementById("category").value,
            event_date: document.getElementById("eventDate").value,
            total_seats: Number(
                document.getElementById("totalSeats").value
            ),
            base_price: Number(
                document.getElementById("basePrice").value
            )
        };

        try {
            const result = await apiRequest(`${API_URL}/events`, {
                method: "POST",
                body: JSON.stringify(eventData)
            });

            showObject(
                "eventMessage",
                "Event Created Successfully!",
                result,
                {
                    background: "#f7f6ff",
                    borderColor: "#c9c2f4"
                }
            );

            document.getElementById("eventForm").reset();
        } catch (error) {
            showError("eventMessage", error);
        }
    }
);

// ------------------------------
// 2. Find an event
// ------------------------------

document.getElementById("searchEventForm").addEventListener(
    "submit",
    async event => {
        event.preventDefault();

        const id = document.getElementById("searchEventId").value;

        try {
            const result = await apiRequest(
                `${API_URL}/events/${id}`
            );

            showObject(
                "eventDetails",
                "Event Details",
                result
            );
        } catch (error) {
            showError("eventDetails", error);
        }
    }
);

// ------------------------------
// 3. Book tickets
// ------------------------------

document.getElementById("bookingForm").addEventListener(
    "submit",
    async event => {
        event.preventDefault();

        const seatText =
            document.getElementById("seatNumbers").value.trim();

        const seatNumbers = seatText
            .split(",")
            .map(number => number.trim())
            .map(Number);

        if (
            !seatText ||
            seatNumbers.some(number =>
                !Number.isInteger(number) || number <= 0
            )
        ) {
            showMessage(
                "bookingMessage",
                "Enter valid seat numbers separated by commas, for example: 1,2,3."
            );
            return;
        }

        const bookingData = {
            event_id: Number(
                document.getElementById("bookingEventId").value
            ),
            customer_name:
                document.getElementById("customerName").value.trim(),
            customer_email:
                document.getElementById("customerEmail").value.trim(),
            seat_numbers: seatNumbers
        };

        try {
            const result = await apiRequest(`${API_URL}/bookings`, {
                method: "POST",
                body: JSON.stringify(bookingData)
            });

            const confirmed = result.status === "CONFIRMED";

            showObject(
                "bookingMessage",
                confirmed ? "Booking Confirmed!" : "Booking Rejected",
                result,
                {
                    background: confirmed ? "#e8f7ee" : "#fff0f0",
                    borderColor: confirmed ? "#a6dfba" : "#f0b4b4",
                    titleColor: confirmed ? "#176b38" : "#a12626"
                }
            );

            document.getElementById("bookingForm").reset();
        } catch (error) {
            showError("bookingMessage", error);
        }
    }
);

// ------------------------------
// 4. Find a booking
// ------------------------------

document.getElementById("searchBookingForm").addEventListener(
    "submit",
    async event => {
        event.preventDefault();

        const id =
            document.getElementById("searchBookingId").value;

        try {
            const result = await apiRequest(
                `${API_URL}/bookings/${id}`
            );

            const confirmed = result.status === "CONFIRMED";

            showObject(
                "bookingDetails",
                "Booking Details",
                result,
                {
                    background: confirmed ? "#f7fcf8" : "#fff8f8",
                    borderColor: confirmed ? "#c7e8d1" : "#f0d0d0"
                }
            );
        } catch (error) {
            showError("bookingDetails", error);
        }
    }
);

// ------------------------------
// 5. View event information
// ------------------------------

document.getElementById("eventInfoForm").addEventListener(
    "submit",
    async event => {
        event.preventDefault();

        const id = document.getElementById("infoEventId").value;
        const type = document.getElementById("infoType").value;

        let endpoint;
        let title;

        if (type === "seats") {
            endpoint = `${API_URL}/events/${id}/seats`;
            title = "Seat Availability";
        } else if (type === "summary") {
            endpoint = `${API_URL}/events/${id}/summary`;
            title = "Event Summary";
        } else {
            endpoint = `${API_URL}/events/${id}/bookings`;
            title = "Booking History";
        }

        try {
            const result = await apiRequest(endpoint);
            const container = document.getElementById("eventInfo");

            container.replaceChildren();

            if (Array.isArray(result)) {
                if (result.length === 0) {
                    showMessage(
                        "eventInfo",
                        "No bookings found for this event.",
                        true
                    );
                    return;
                }

                container.appendChild(
                    createElement("h3", title, {
                        color: "#29245c"
                    })
                );

                result.forEach((booking, index) => {
                    if (booking && typeof booking === "object") {
                        renderObjectCard(
                            container,
                            `Booking ${booking.id ?? index + 1}`,
                            booking
                        );
                    }
                });

                return;
            }

            showObject("eventInfo", title, result);
        } catch (error) {
            showError("eventInfo", error);
        }
    }
);
