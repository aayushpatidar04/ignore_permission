frappe.pages['schedule-board-next7'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Schedule Board: Next 7 Days',
		single_column: true
	});

	let script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/js/bootstrap.bundle.min.js";
    document.head.appendChild(script);

	const pageKey = 'reload_schedule_board_next';

    // Check if this page has been visited before
    if (!localStorage.getItem(pageKey)) {
        // If it's the first time, reload the page
        localStorage.setItem(pageKey, 'visited'); // Mark the page as visited
        window.location.reload(); // Reload the page
        return; // Exit the function to avoid further execution
    }
	localStorage.removeItem(pageKey);

	page.set_title("Schedule Board: Next 7 Days");
	frappe.call({
		method: "field_service_management.field_service_management.page.schedule_board_next7.schedule_board_next7.get_context",
		callback: function (r) {
			if (r.message) {
				$(frappe.render_template("schedule_board_next7", r.message, r.issues)).appendTo(page.body);
			} else {
				console.log("No message returned from the server.");
			}
		}
	});
	$(document).ready(function () {


		$(document).on("click", ".submit", function () {
			const issueId = $(this).data("issue");
			const form = $("#custom-form-" + issueId);

			// Collect form data
			const formData = {
				code: form.find(".code").val(),
				technicians: form.find(".technician").val(),
				date: form.find(".date").val(),
				stime: form.find(".stime").val(),
				etime: form.find(".etime").val()
			};

			// Make an API call to Frappe to save the data in your Doctype
			frappe.call({
				method: "field_service_management.field_service_management.page.schedule_board_next7.schedule_board_next7.save_form_data",
				args: {
					form_data: formData
				},
				callback: function (response) {
					if (response.message.success) {
						alert("Maintenance Visit scheduled successfully!");
						window.location.reload();
					} else {
						alert(`Form submission failed!" ${response.message.message}`);
					}
				},
				error: function (error) {
					console.error(error);
					alert("An error occurred while submitting the form!");
				}
			});
		});

		$(document).on('shown.bs.modal', '.issue-modal', function () {
			const issueId = $(this).attr('id').replace('issueModal', '');
			const mapContainerId = 'map-' + issueId;
			const geoDiv = $('#map-' + issueId);

			const geoDataString = geoDiv.attr('data-geo').replace(/'/g, '"');
			const geoData = JSON.parse(geoDataString);

			if (!geoDiv.length) {
				console.error('Map container not found:', mapContainerId);
				return;
			}

			if (geoDiv.data('mapInstance')) {
				geoDiv.data('mapInstance').remove();
				geoDiv.removeData('mapInstance'); // Clear the stored map instance
			}

			const map = L.map(mapContainerId).setView([0, 0], 13);
			geoDiv.data('mapInstance', map);

			frappe.call({
				method: "field_service_management.field_service_management.page.schedule_board_next7.schedule_board_next7.get_cords",
				callback: function (r) {
					if (r.message) {
						const technicians = r.message;

						// Check if the map container exists
						let customerLat = null;
						let customerLng = null;

						// Add shapes/markers from geoData
						geoData.forEach(feature => {
							const { properties, geometry } = feature;
							const [lng, lat] = geometry.coordinates;

							if (Object.keys(properties).length === 0) {
								customerLat = lat;
								customerLng = lng;
							} else if (properties.point_type === 'circle' && properties.radius) {
								L.circle([lat, lng], {
									radius: properties.radius,
									color: 'blue',
									fillColor: '#30a0ff',
									fillOpacity: 0.3
								}).addTo(map).bindPopup(`<b>Circle with radius: 300 meters</b>`);
							}
						});

						// Center the map on the customer's location
						if (customerLat !== null && customerLng !== null) {
							map.setView([customerLat, customerLng], 13);
							L.marker([customerLat, customerLng]).addTo(map)
								.bindPopup('<b>Customer Location</b>').openPopup();
						}

						// Add OpenStreetMap tiles
						L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
							maxZoom: 19,
							attribution: '&copy; OpenStreetMap contributors'
						}).addTo(map);

						// Add technician markers
						const greenIcon = L.icon({
							iconUrl: '/private/files/green-marker51773a.png',
							iconSize: [25, 41],
							iconAnchor: [12, 41],
							popupAnchor: [1, -34]
						});

						technicians.forEach(tech => {
							L.marker([tech.latitude, tech.longitude], { icon: greenIcon }).addTo(map)
								.bindPopup('<b>Technician: ' + tech.technician + '</b>');
						});
					} else {
						console.log("No cords returned from the server.");
					}
				}
			});
		});


		let liveMap = null;
		let updateInterval = null;

		$(document).on('shown.bs.modal', '#mapModal', function () {
			const mapContainerId = 'live-map-container';
			const mapDiv = $('#' + mapContainerId);

			// Remove existing map instance if any (to prevent re-initialization error)
			if (liveMap) {
				liveMap.remove();
				liveMap = null;
			}

			// Initialize the map
			liveMap = L.map(mapContainerId).setView([0, 0], 5); // Initial view centered on India
			L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
				maxZoom: 19,
				attribution: '&copy; OpenStreetMap contributors'
			}).addTo(liveMap);

			// Define custom icons for technicians and maintenance visits
			const technicianIcon = L.icon({
				iconUrl: '/private/files/green-marker51773a.png',
				iconSize: [25, 41],
				iconAnchor: [12, 41],
				popupAnchor: [1, -34]
			});

			// Function to fetch and display locations
			function fetchAndDisplayLocations() {
				frappe.call({
					method: "field_service_management.field_service_management.page.schedule_board_next7.schedule_board_next7.get_live_locations",
					callback: function (r) {
						if (r.message) {
							const { technicians, maintenance } = r.message;

							// Clear existing markers before adding new ones
							liveMap.eachLayer(function (layer) {
								if (layer instanceof L.Marker) {
									liveMap.removeLayer(layer);
								}
							});

							// Add technician markers
							technicians.forEach(tech => {
								L.marker([tech.latitude, tech.longitude], { icon: technicianIcon })
									.addTo(liveMap)
									.bindPopup(`<b>Technician: ${tech.technician}</b><br>Lat: ${tech.latitude}, Lng: ${tech.longitude}`);
							});

							// Add maintenance visit markers
							maintenance.forEach(visit => {
								let customerLat = null;
								let customerLng = null;
								if (visit.geolocation && visit.geolocation.features && Array.isArray(visit.geolocation.features)) {
									visit.geolocation.features.forEach(function(feature) {
										const { properties, geometry } = feature;
										
										// Extract latitude and longitude from coordinates
										const [lng, lat] = geometry.coordinates;
								
										// Check if properties are empty
										if (Object.keys(properties).length === 0) {
											customerLat = lat;
											customerLng = lng;
										} else if (properties.point_type === 'circle' && properties.radius) {
											// Handle case for circle type with radius
											L.circle([lat, lng], {
												radius: properties.radius,
												color: 'blue',
												fillColor: '#30a0ff',
												fillOpacity: 0.3
											}).addTo(map).bindPopup(`<b>Circle with radius: ${properties.radius} meters</b>`);
										}
									});
								} else {
									console.error('Geolocation data is not in the correct format or missing');
								}
								
								if (customerLat !== null && customerLng !== null) {
									liveMap.setView([customerLat, customerLng], 13);
									L.marker([customerLat, customerLng])
										.addTo(liveMap)
										.bindPopup(`<b>Maintenance Visit</b><br>${visit.visit_id}<br>${visit.address}`);
								}
							});
						} else {
							console.log("No data returned from the server.");
						}
					}
				});
			}

			// Fetch and display the initial set of locations
			fetchAndDisplayLocations();

			// Set an interval to update locations periodically (every 30 seconds)
			updateInterval = setInterval(fetchAndDisplayLocations, 30000);
		});

		// Clean up when the modal is hidden
		$(document).on('hidden.bs.modal', '#liveLocationModal', function () {
			if (liveMap) {
				liveMap.remove();
				liveMap = null;
			}
			if (updateInterval) {
				clearInterval(updateInterval);
				updateInterval = null;
			}
		});

		setTimeout(function () {
			
			var drags = $('.drag');
			$('.drag').each(function () {
				$(this).on('dragstart', function (e) {
					e.originalEvent.dataTransfer.setData('text/plain', this.id); // Store the ID of the dragging card
					setTimeout(() => {
						$(this).css('opacity', '0.5'); // Visual feedback on drag start
					}, 0);
				});

				$(this).on('dragend', function () {
					$(this).css('opacity', '1'); // Reset opacity on drag end
				});
			});

			var dropZones = $('.drop-zone');

			$('.drop-zone').each(function () {
				$(this).on('dragover', function (e) {
					e.preventDefault(); // Prevent default to allow drop
					$(this).addClass('drop-hover'); // Add hover class
					$(this).css('background-color', 'green'); // Change background color to green
				});

				$(this).on('dragleave', function () {
					$(this).removeClass('drop-hover'); // Remove hover class
					$(this).css('background-color', 'cyan'); // Reset background color
				});

				$(this).on('drop', function (e) {
					e.preventDefault(); // Prevent default action
					const cardId = e.originalEvent.dataTransfer.getData('text/plain'); // Get the ID of the dragged card
					const slotTime = $(this).data('time');
					const not_available = $(this).data('na');
					const tech = $(this).data('tech');
					const card = $('#' + cardId);
					const slotDate = $(this).data('date');

					$(this).removeClass('drop-hover'); // Remove hover class
					$(this).css('background-color', 'cyan'); // Reset background color
					// Open modal for the dropped card using its issue name
					if(card.data('type') == 'type1'){
						openModal(cardId, slotTime, tech, not_available, slotDate);
					}else if(card.data('type') == 'type2'){
						const duration = card.data('duration');
						openModal2(cardId, slotTime, tech, duration, not_available, slotDate);
					}
				});
			});

			function openModal(issueName, slot, tech, na, slotDate) {
				const modalId = `formModal${issueName}`; // Construct the modal ID
				const modal = $(`#${modalId}`); // Select the modal using jQuery

				if (modal.length) { // Check if the modal exists
					const modalInstance = new bootstrap.Modal(modal[0]); // Pass the raw DOM element to bootstrap.Modal
					const currentDate = new Date();
					currentDate.setDate(currentDate.getDate() - 1);
					const year = currentDate.getFullYear();
					const month = String(currentDate.getMonth() + 1).padStart(2, '0'); // Months are 0-indexed
					const day = String(currentDate.getDate()).padStart(2, '0');
					modalInstance.show(); // Show the modal
					const [hours, minutes, seconds] = slot.split(':').map(Number);
					if (hours < 10) {
						const stime_val = '0' + slot.substring(0, 4)
						modal.find('.stime').val(stime_val);
						modal.find('.etime').data('stime', slot.substring(0, 4));
					} else {
						modal.find('.stime').val(slot.substring(0, 5));
						modal.find('.etime').data('stime', slot.substring(0, 5));
					}
					modal.find('.technician').val(tech).change();
					if(typeof na === 'string'){
						try {
							na = JSON.parse(na.replace(/'/g, '"')); // Convert single quotes to double quotes and parse the string
						} catch (e) {
							console.error('Error parsing na:', e);
						}
						$.each(na, function(index, value) {
							const option = modal.find('.technician option[value="' + value + '"]');
							
							if (option.length) {
								option.prop('disabled', true);
								option.css('color', 'red');
							}
						});
					}else{
						modal.find('.technician option').prop('disabled', false).css('color', '');
					}
					const formattedDate = `${year}-${month}-${day}`;
					modal.find('.date').val(slotDate);
				} else {
					console.error(`Modal with ID ${modalId} not found.`);
				}
			}


			function openModal2(issueName, slot, tech, duration, na, slotDate) {
				const modalId = `taskModal${issueName}`; // Construct the modal ID
				const modal = $(`#${modalId}`); // Select the modal using jQuery
				if (modal.length) { // Check if the modal exists
					const modalInstance = new bootstrap.Modal(modal[0]); // Pass the raw DOM element to bootstrap.Modal
					const currentDate = new Date();
					currentDate.setDate(currentDate.getDate() - 1);
					const year = currentDate.getFullYear();
					const month = String(currentDate.getMonth() + 1).padStart(2, '0'); // Months are 0-indexed
					const day = String(currentDate.getDate()).padStart(2, '0');
					modalInstance.show(); // Show the modal
					const [hours, minutes, seconds] = slot.split(':').map(Number);
					let startTime = new Date();
					startTime.setDate(currentDate.getDate() - 1);
					startTime.setHours(hours, minutes, seconds);
					let etime = new Date(startTime.getTime() + duration * 60 * 60 * 1000);
					if (hours < 10) {
						const stime_val = '0' + slot.substring(0, 4)
						modal.find('.stime').val(stime_val);
						modal.find('.etime').data('stime', slot.substring(0, 4));
					} else {
						modal.find('.stime').val(slot.substring(0, 5));
						modal.find('.etime').data('stime', slot.substring(0, 5));
					}
					modal.find('.etime').val(etime.toTimeString().substring(0, 5));
					modal.find('.technician').val(tech).change();
					if(typeof na === 'string'){
						try {
							na = JSON.parse(na.replace(/'/g, '"')); // Convert single quotes to double quotes and parse the string
						} catch (e) {
							console.error('Error parsing na:', e);
						}
						$.each(na, function(index, value) {
							const option = modal.find('.technician option[value="' + value + '"]');
							
							if (option.length) {
								option.prop('disabled', true);
								option.css('color', 'red');
							}
						});
					}else{
						modal.find('.technician option').prop('disabled', false).css('color', '');
					}
					const formattedDate = `${year}-${month}-${day}`;
					modal.find('.date').val(slotDate);
				} else {
					console.error(`Modal with ID ${modalId} not found.`);
				}
			}
			$(document).on('click', '.close', function () {
				$(this).closest('.modal').modal('hide'); // Ensure the modal hides on close
			});
			$('.technician').select2();

			var etime = $('.etime');
			etime.each(function () {
				$(this).on('change', function (e) {
					setTimeout(() => {
						const timeValue = $(this).val();
						const stime = $(this).data('stime').split(':');
						if (timeValue) {
							const [hours, minutes] = timeValue.split(':').map(Number);
							if (minutes % 30 !== 0) {
								alert('Please select a time that is a multiple of 30 minutes.');
								$(this).val(''); // Clear the input
								$(this).focus(); // Focus back on the input
							}else if(stime[0] >= hours){
								alert('Please select a time that is greater than start time.');
								$(this).val(''); // Clear the input
								$(this).focus();
							}
						}
					}, 1000);  // Focus back on the input
				});
			});

			$('.nav-link').on('click', function(event) {
				// Prevent default action
				event.preventDefault();
	
				$('.nav-link').removeClass('active');
				$('.tab-pane').removeClass('show active');
	
				$(this).addClass('active');
	
				var contentId = $(this).attr('aria-controls');
				
				$('#' + contentId ).addClass('show active');
			});
		}, 1000);

		//update modal
		$(document).on("click", ".update", function () {
			const issueId = $(this).data("issue");
			const form = $("#custom2-form-" + issueId);

			// Collect form data
			const formData = {
				code: form.find(".code").val(),
				technicians: form.find(".technician").val(),
				date: form.find(".date").val(),
				stime: form.find(".stime").val(),
				etime: form.find(".etime").val()
			};

			// Make an API call to Frappe to save the data in your Doctype
			frappe.call({
				method: "field_service_management.field_service_management.page.schedule_board_next7.schedule_board_next7.update_form_data",
				args: {
					form_data: formData
				},
				callback: function (response) {
					if (response.message.success) {
						alert("Maintenance Visit updated successfully!");
						window.location.reload();
					} else {
						alert(`Form submission failed!" ${response.message.message}`);
					}
				},
				error: function (error) {
					console.error(error);
					alert("An error occurred while submitting the form!");
				}
			});

		});

	});
}