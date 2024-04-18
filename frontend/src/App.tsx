import { useEffect, useState } from "react";
import "./App.css";
import { useCookies } from "react-cookie";
import axios from "axios";

interface User {
    user_id: string;
    ai_name: string;
    human_name: string;
}

function App() {
    const [cookies, setCookie, _removeCookie] = useCookies(["myUser"]);
    const [users, setUsers] = useState([] as User[]);

    const [myUser, setMyUser] = useState(cookies["myUser"] as User | undefined);

    useEffect(() => {
        const getUserIds = async () => {
            try {
                const response = await axios.get("http://0.0.0.0:8000/users");
                setUsers(response.data as User[]);
            } catch (error) {
                console.error("couldn't fetch users", error);
            }
        };

        getUserIds();

        return () => {};
    }, []);

    return (
        <>
            <header>
                <div>
                    <p>
                        Your cookie says you are{" "}
                        {myUser ? myUser.human_name : ""}
                    </p>
                </div>
                <nav className="userIdsNav">
                    {users.map((user: User, index) => (
                        <a
                            onClick={() => {
                                setMyUser(user);
                                setCookie("myUser", user);
                            }}
                            href=""
                            key={index}
                        >
                            {user.human_name}: {user.ai_name}
                        </a>
                    ))}
                </nav>
            </header>
            {/* <main>tests</main> */}
            {/* <footer>atesate</footer> */}
        </>
    );
}

export default App;
