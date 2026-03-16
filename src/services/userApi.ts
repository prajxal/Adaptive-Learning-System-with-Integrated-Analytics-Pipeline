import BACKEND_URL, { getClerkToken } from "./api";

export async function getUserProfile() {
    const response = await fetch(`${BACKEND_URL}/users/me/profile`, {
        headers: {
            Authorization: `Bearer ${await getClerkToken()}`,
            "Content-Type": "application/json"
        }
    });

    if (!response.ok) throw new Error("Failed to fetch user profile");
    return response.json();
}

export async function getUserSkills() {
    console.log("Token:", await getClerkToken());

    const response = await fetch(`${BACKEND_URL}/users/me/skills`, {
        headers: {
            Authorization: `Bearer ${await getClerkToken()}`,
            "Content-Type": "application/json"
        }
    });

    console.log("Response status:", response.status);

    const text = await response.text();
    console.log("Response body:", text);

    if (!response.ok) throw new Error(text);

    return JSON.parse(text);
}
