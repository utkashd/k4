import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import DataTable from "react-data-table-component";
import { BsFillTrash3Fill } from "react-icons/bs";

function ManageUsers({
    users,
    serverUrl,
    currentAdminUser,
}: {
    users: User[];
    serverUrl: URL;
    currentAdminUser: User;
}) {
    const [selectedRows, setSelectedRows] = useState([] as User[]);
    const [toggleCleared, setToggleCleared] = useState(false);
    const handleRowSelected = useCallback(
        (selected: {
            allSelected: boolean;
            selectedCount: number;
            selectedRows: User[];
        }) => {
            setSelectedRows(selected.selectedRows);
        },
        []
    );
    return (
        <>
            <UsersList
                users={users}
                handleRowSelected={handleRowSelected}
                toggleCleared={toggleCleared}
                currentAdminUser={currentAdminUser}
            />
            <DeactivateUsersBar
                serverUrl={serverUrl}
                selectedRows={selectedRows}
                toggleCleared={toggleCleared}
                setToggleCleared={setToggleCleared}
            />
        </>
    );
}

function DeactivateUsersBar({
    selectedRows: selectedUsers,
    serverUrl,
    toggleCleared,
    setToggleCleared,
}: {
    selectedRows: User[];
    serverUrl: URL;
    toggleCleared: boolean;
    setToggleCleared: React.Dispatch<React.SetStateAction<boolean>>;
}) {
    if (!selectedUsers.length) {
        return <></>;
    }

    const emails = selectedUsers.map((user: User) => {
        return user.user_email;
    });
    const confirmDeactivateUsers = async () => {
        const doesAdminWantToDeactivateSelectedUsers = confirm(
            `Deactivate the following users? ${emails.join(" ")}`
        );
        if (doesAdminWantToDeactivateSelectedUsers) {
            for (const user of selectedUsers) {
                await axios.delete(new URL("/user", serverUrl).toString(), {
                    withCredentials: true,
                    data: user,
                });
                setToggleCleared(!toggleCleared);
            }
        }
    };
    return (
        <>
            <a
                href=""
                onClick={(event) => {
                    event.preventDefault();
                }}
            >
                <BsFillTrash3Fill
                    onClick={(event) => {
                        event.preventDefault();
                        confirmDeactivateUsers();
                    }}
                />
            </a>
        </>
    );
}

function UsersList({
    users,
    handleRowSelected,
    toggleCleared,
    currentAdminUser,
}: {
    users: User[];
    handleRowSelected: (selected: {
        allSelected: boolean;
        selectedCount: number;
        selectedRows: User[];
    }) => void;
    toggleCleared: boolean;
    currentAdminUser: User;
}) {
    const columns = [
        {
            name: "user_id",
            selector: (user: User) => user.user_id,
            sortable: true,
        },
        {
            name: "Email",
            selector: (user: User) => user.user_email,
            sortable: true,
        },
        {
            name: "Name",
            selector: (user: User) => user.human_name,
            sortable: true,
        },
        {
            name: "Admin?",
            selector: (user: User) => (user.is_user_an_admin ? "yes" : "no"),
            sortable: true,
        },
        {
            name: "Deactivated?",
            selector: (user: User) => (user.is_user_deactivated ? "yes" : "no"),
            sortable: true,
        },
        {
            name: "Email verified?",
            selector: (user: User) =>
                user.is_user_email_verified ? "yes" : "no",
            sortable: true,
        },
    ];

    const isUserNotSelectable = (user: User) => {
        return user.user_email === currentAdminUser.user_email;
    };

    return (
        <>
            <div style={{ padding: "20px" }}>
                <DataTable
                    columns={columns}
                    data={users}
                    keyField="user_id"
                    striped
                    highlightOnHover
                    theme="dark"
                    pagination
                    selectableRows
                    onSelectedRowsChange={handleRowSelected}
                    clearSelectedRows={toggleCleared}
                    selectableRowDisabled={isUserNotSelectable}
                />
            </div>
        </>
    );
}

const AdminPanel = ({
    currentAdminUser,
    serverUrl,
}: {
    currentAdminUser: User;
    serverUrl: URL;
}) => {
    const [users, setUsers] = useState<User[]>([]);
    useEffect(() => {
        const getUsers = async () => {
            const response = await axios.get(
                new URL("/user", serverUrl).toString(),
                { withCredentials: true }
            );
            setUsers(response.data);
        };
        getUsers();
    }, []);

    return (
        <>
            Welcome Admin {currentAdminUser.user_email}. Here you may create and
            deactivate users.
            <br />
            <br />
            <ManageUsers
                users={users}
                serverUrl={serverUrl}
                currentAdminUser={currentAdminUser}
            />
        </>
    );
};

export default AdminPanel;
