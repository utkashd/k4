import { AxiosInstance } from "axios";

interface Server {
    url: URL;
    api: AxiosInstance;
}

export default Server;
