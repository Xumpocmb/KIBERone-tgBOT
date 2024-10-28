document.addEventListener("DOMContentLoaded", function () {
        if (window.Telegram.WebApp) {
            const initData = window.Telegram.WebApp.initData;
            const nameElement = document.getElementById("fullname");
            const birthdayElement = document.getElementById("dob");
            const locationElement = document.getElementById("location");
            const subjectElement = document.getElementById("subject");
            const resumeElement = document.getElementById("resumeInfo");
            const kiberonsElement = document.getElementById("kiberons");

            const contentElement = document.getElementById("main");
            const loaderElement = document.getElementById("loader");

            loaderElement.style.display = 'block';
            contentElement.style.display = 'none';


            fetch("/kiberclub/data_from_page/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({initData: initData}),
            })
                .then(response => {
                    if (response.ok) {
                        return response.json();
                    }
                })
                .then(data => {
                    if (data.status === "success") {
                        loaderElement.style.display = 'none';
                        contentElement.style.display = 'block';
                        nameElement.innerText = data.data.user_crm_name;
                        birthdayElement.innerText = data.data.user_crm_birthday;
                        locationElement.innerText = data.data.user_crm_location;
                        subjectElement.innerText = data.data.lesson_name;
                        resumeElement.innerText = data.data.intermediate_resume;
                        kiberonsElement.innerText = data.data.kiberons;
                    }
                })
                .catch(error => {
                    console.error("Error:", error.message);
                    loaderElement.style.display = 'none';
                    contentElement.style.display = 'block';
                });
        }
        else {
            console.log("Telegram WebApp is not available");
            const span = document.getElementById("backend_info");
            span.innerText = "Telegram WebApp is not available";
        }
    }
);
