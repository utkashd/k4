import Server from "../model/Server";

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
        await server.api.post("/logout");
        setCurrentUserAndCookie(null);
        window.location.reload(); // TODO need to fix underlying issue so this isn't necessary
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
