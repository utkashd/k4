import Server from "../model/Server";
import { User } from "../model/User";

export const CurrentUserAndLogoutButton = ({
    currentUser,
    server,
    setCurrentUserAndCookie,
}: {
    currentUser: User | null;
    server: Server | null;
    setCurrentUserAndCookie: (user: User | null) => void;
}) => {
    if (!currentUser || !server) {
        return <>You're not logged in.</>;
    }

    const logout = async () => {
        await server.api.post("/logout", {}, { withCredentials: true });
        setCurrentUserAndCookie(null);
        window.location.reload(); // TODO need to fix underlying issue so this isn't necessary
    };
    return (
        <div
            style={{
                padding: 10,
                overflowWrap: "break-word",
            }}
        >
            Logged in as {currentUser.user_email}
            <br />
            <a onClick={logout}>logout</a>
        </div>
    );
};

const RightSidePanelContents = ({
    currentUser,
    server,
    setCurrentUserAndCookie,
}: {
    currentUser: User;
    server: Server;
    setCurrentUserAndCookie: (user: User | null) => void;
}) => {
    return (
        <CurrentUserAndLogoutButton
            currentUser={currentUser}
            server={server}
            setCurrentUserAndCookie={setCurrentUserAndCookie}
        />
    );
};

export default RightSidePanelContents;
