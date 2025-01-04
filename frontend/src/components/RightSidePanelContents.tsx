import axios from "axios";

const CurrentUserAndLogoutButton = ({
    currentUser,
    serverUrl,
    setCurrentUserAndCookie,
}: {
    currentUser: User | null;
    serverUrl: URL | null;
    setCurrentUserAndCookie: (user: User | null) => void;
}) => {
    if (!currentUser || !serverUrl) {
        return <>You're not logged in.</>;
    }

    const logout = async () => {
        setCurrentUserAndCookie(null);
        await axios.post(new URL("/logout", serverUrl).toString());
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
    serverUrl,
    setCurrentUserAndCookie,
}: {
    currentUser: User | null;
    serverUrl: URL | null;
    setCurrentUserAndCookie: (user: User | null) => void;
}) => {
    return (
        <CurrentUserAndLogoutButton
            currentUser={currentUser}
            serverUrl={serverUrl}
            setCurrentUserAndCookie={setCurrentUserAndCookie}
        />
    );
};

export default RightSidePanelContents;
