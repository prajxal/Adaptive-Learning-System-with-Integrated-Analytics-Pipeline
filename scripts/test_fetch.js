const BACKEND_URL = "http://localhost:8000";
const currentRoadmapId = "python-developer";
// Try to get token from sqlite if available, otherwise just use dummy
const token = "dummy-token"; // we will see if we get a 401

async function run() {
    try {
        console.log("DEBUG: token =", token);
        console.log("DEBUG: BACKEND_URL =", BACKEND_URL);

        const res = await fetch(
            `${BACKEND_URL}/recommend?current_roadmap_id=${currentRoadmapId}`,
            {
                headers: {
                    "Content-Type": "application/json",
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
                }
            }
        );

        console.log("DEBUG: status =", res.status);

        const text = await res.text();
        console.log("DEBUG: raw response =", text);

    } catch (err) {
        console.error("Fetch threw:", err);
    }
}
run();
