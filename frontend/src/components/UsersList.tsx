import "./UsersList.css";

function UsersList({
    users,
    setMyUser,
}: {
    users: User[];
    setMyUser: (user: User) => void;
}) {
    return (
        <>
            <div className="users-list">
                {users.map((user: User) => (
                    <div key={user.user_id}>
                        <a
                            onClick={(event) => {
                                event.preventDefault();
                                setMyUser(user);
                            }}
                            href=""
                        >
                            {user.human_name}
                        </a>
                        {/* <BsFillTrash3Fill
                                onClick={(event) => {
                                    deleteUser(event);
                                }}
                            /> */}
                    </div>
                ))}
            </div>
        </>
    );
}

export default UsersList;
