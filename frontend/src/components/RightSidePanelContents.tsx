import Server from "../model/Server";

const CurrentUserAndLogoutButton = ({
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
        setCurrentUserAndCookie(null);
        await server.api.post("/logout");
    };
    return (
        <>
            You're logged in as {currentUser.user_email}
            <br />
            <br />
            <a onClick={logout}>logout</a>
        </>
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
