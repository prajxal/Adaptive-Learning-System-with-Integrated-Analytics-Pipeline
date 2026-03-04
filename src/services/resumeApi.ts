import BACKEND_URL from "./api";

export async function uploadResume(file: File) {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${BACKEND_URL}/resume/upload`, {
        method: "POST",
        headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: formData,
    });

    if (!res.ok) throw new Error("Resume upload failed");

    return res.json();
}

export async function checkResumeStatus() {
    const res = await fetch(`${BACKEND_URL}/resume/status`, {
        method: "GET",
        headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
    });

    if (!res.ok) throw new Error("Failed to fetch resume status");

    return res.json();
}
