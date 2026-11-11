
import axios from "axios";

const API_URL = "http://127.0.0.1:8000";

export const analyzeResume = async (file, jd) => {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("jd", jd);

  const response = await axios.post(
    `${API_URL}/analyze/suggestions`,
    formData
  );

  return response.data;
};
