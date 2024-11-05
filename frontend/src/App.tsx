import { useEffect, useState } from "react";
import "./App.css";
import { useCookies } from "react-cookie";
import axios from "axios";
import CreateUser from "./components/CreateUser";
import SignedInAs from "./components/SignedInAs";
import UsersList from "./components/UsersList";
import ChatBox from "./components/ChatBox";

declare global {
    var _inspectBackend: () => void;
}
/**
 * When developing, it's sometimes useful to check stuff in the api server. This starts
 * a breakpoint in the backend.
 *
 * In the browser console, I `await _inspectBackend()` and then move to the
 * terminal for the api server.
 */
// var _inspectBackend = async () => {
//     try {
//         await axios.post("http://localhost:8000/_inspect");
//     } catch (error) {
//         console.log(error);
//     }
// };
// globalThis._inspectBackend = _inspectBackend;

function App() {
    const [cookies, setCookie, _removeCookie] = useCookies(["myUser"]);
    const [users, setUsers] = useState({} as Record<string, User>);

    const [myUser, setMyUser] = useState(null as User | null);

    const setMyUserAndSetTheMyUserCookie = (user: User | null) => {
        setMyUser(user);
        setCookie("myUser", user);
    };

    const refreshUsers = async () => {
        try {
            const response = await axios.get("http://localhost:8000/users");
            const usersList: User[] = response.data as User[];
            const usersByUserId: Record<string, User> = {};
            usersList.forEach((user: User) => {
                usersByUserId[user.user_id] = user;
            });
            setUsers(usersByUserId);
            if (cookies["myUser"]) {
                const myUserCookie = cookies["myUser"] as User;
                if (Object.keys(usersByUserId).includes(myUserCookie.user_id)) {
                    setMyUser(usersByUserId[myUserCookie.user_id]);
                }
            }
        } catch (error) {
            console.error(
                "couldn't fetch users. the backend is probably down",
                error
            );
            setUsers({});
        }
    };

    useEffect(() => {
        const source = axios.CancelToken.source();

        setTimeout(() => {
            refreshUsers();
        }, 1000);

        return () => {
            source.cancel();
        };
    }, []);

    return (
        <>
            <div className="app-container">
                <div className="left-side-panel">
                    <img src="./gh.png" className="logo-test"></img>
                </div>
                <div className="main-panel">
                    <ChatBox user={myUser} />
                </div>
                <div className="right-side-panel">
                    <UsersList
                        users={users}
                        refreshUsers={refreshUsers}
                        myUser={myUser}
                        setMyUser={setMyUserAndSetTheMyUserCookie}
                    />
                    <SignedInAs
                        myUser={myUser}
                        setMyUser={setMyUserAndSetTheMyUserCookie}
                    />
                    <CreateUser refreshUsers={refreshUsers} />
                </div>
            </div>
        </>
    );
}

export default App;
