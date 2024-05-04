import { BsFillTrash3Fill } from "react-icons/bs";
import "./UsersList.css";
import axios from "axios";

function UsersListItem({
    user,
    refreshUsers,
    myUser,
    setMyUser,
}: {
    user: User;
    refreshUsers: () => void;
    myUser: User | null;
    setMyUser: (user: User | null) => void;
}) {
    const deleteUser = async (
        event: React.MouseEvent<SVGElement, MouseEvent>,
        userToDelete: User
    ) => {
        event.preventDefault();
        const theyAreSureTheyWantToDelete = confirm(
            `Are you sure you want to delete user "${userToDelete.human_name}"?`
        );
        if (!theyAreSureTheyWantToDelete) {
            return;
        }
        if (myUser && userToDelete.user_id === myUser.user_id) {
            setMyUser(null);
            console.log("hi");
        }
        try {
            await axios.delete("http://localhost:8000/user", {
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                data: { user_id: userToDelete.user_id },
            });
            refreshUsers();
        } catch (error) {
            console.log("failed to delete a user", userToDelete, error);
        }
    };

    return (
        <>
            <a
                onClick={(event) => {
                    event.preventDefault();
                    setMyUser(user);
                }}
                href=""
            >
                {user.human_name}
            </a>
            <a
                href=""
                onClick={(event) => {
                    event.preventDefault();
                }}
            >
                <BsFillTrash3Fill
                    onClick={(event) => {
                        deleteUser(event, user);
                    }}
                />
            </a>
        </>
    );
}

function UsersList({
    users,
    refreshUsers,
    myUser,
    setMyUser,
}: {
    users: Record<string, User>;
    refreshUsers: () => void;
    myUser: User | null;
    setMyUser: (user: User | null) => void;
}) {
    // TODO refresh messages when changing the user
    return (
        <>
            <div className="users-list">
                {Object.entries(users).map(([user_id, user]) => {
                    return (
                        <div key={user_id}>
                            <UsersListItem
                                user={user}
                                refreshUsers={refreshUsers}
                                myUser={myUser}
                                setMyUser={setMyUser}
                            />
                        </div>
                    );
                })}
            </div>
        </>
    );
}

export default UsersList;
