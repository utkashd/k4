import { useEffect, useState } from "react";
import "./App.css";
import { useCookies } from "react-cookie";
import axios from "axios";
import CreateUser from "./components/CreateUser";
import SignedInAs from "./components/SignedInAs";
import UsersList from "./components/UsersList";
import ChatBox from "./components/ChatBox";
// import { BsFillTrash3Fill } from "react-icons/bs";

function App() {
    const [cookies, setCookie, _removeCookie] = useCookies(["myUser"]);
    const [users, setUsers] = useState([] as User[]);

    const [myUser, setMyUser] = useState(null as User | null);

    const setMyUserAndSetTheMyUserCookie = (user: User | null) => {
        setMyUser(user);
        setCookie("myUser", user);
    };

    useEffect(() => {
        const source = axios.CancelToken.source();
        const getUserIds = async () => {
            try {
                const response = await axios.get("http://localhost:8000/users");
                setUsers(response.data as User[]);
                if (cookies["myUser"]) {
                    const myUserCookie = cookies["myUser"] as User;
                    (response.data as User[]).forEach((user: User) => {
                        if (user.user_id === myUserCookie.user_id) {
                            setMyUser(user);
                        }
                    });
                }
            } catch (error) {
                console.error(
                    "couldn't fetch users. the backend is probably down",
                    error
                );
                setUsers([] as User[]);
            }
        };

        setTimeout(() => {
            getUserIds();
        }, 1000);

        return () => {
            source.cancel();
        };
    }, []); // TODO dependent on create user button

    // const deleteUser = async (
    //     event: React.MouseEvent<SVGElement, MouseEvent>
    // ) => {
    //     event.preventDefault();
    //     // try {
    //     //     const response = axios.delete("http://localhost:8000/user")
    //     // }
    // };

    return (
        <>
            <div className="app-container">
                <div className="left-side-panel">
                    <SignedInAs
                        myUser={myUser}
                        setMyUser={setMyUserAndSetTheMyUserCookie}
                    />
                    <UsersList
                        users={users}
                        setMyUser={setMyUserAndSetTheMyUserCookie}
                    />
                    <CreateUser />
                </div>
                <div className="main-panel">
                    <ChatBox user={myUser} />
                </div>
            </div>
        </>
    );
}

export default App;
