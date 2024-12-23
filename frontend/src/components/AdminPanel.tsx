import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import DataTable from "react-data-table-component";
import { FaTrash, FaTrashRestore } from "react-icons/fa";

function ManageUsers({
    serverUrl,
    currentAdminUser,
}: {
    serverUrl: URL;
    currentAdminUser: User;
}) {
    const [users, setUsers] = useState<User[]>([]);
    const refreshUsers = async () => {
        const response = await axios.get(
            new URL("/user", serverUrl).toString(),
            { withCredentials: true }
        );
        setUsers(response.data);
    };
    useEffect(() => {
        refreshUsers();
    }, []);
    const [selectedUsers, setSelectedUsers] = useState([] as User[]);
    const [toggleCleared, setToggleCleared] = useState(false);
    const clearSelection = () => {
        setToggleCleared(!toggleCleared);
        setSelectedUsers([]);
    };
    const handleRowSelected = useCallback(
        (selected: {
            allSelected: boolean;
            selectedCount: number;
            selectedRows: User[];
        }) => {
            setSelectedUsers(selected.selectedRows);
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
            <UserManagementActionsBar
                refreshUsers={refreshUsers}
                serverUrl={serverUrl}
                selectedUsers={selectedUsers}
                clearSelection={clearSelection}
            />
        </>
    );
}

function UserManagementActionsBar({
    refreshUsers,
    selectedUsers,
    serverUrl,
    clearSelection,
}: {
    refreshUsers: () => Promise<void>;
    selectedUsers: User[];
    serverUrl: URL;
    clearSelection: () => void;
}) {
    if (!selectedUsers.length) {
        return <></>;
    }
    const areAllSelectedUsersActive = selectedUsers.every((user: User) => {
        return !user.is_user_deactivated;
    });
    if (areAllSelectedUsersActive) {
        const confirmAndDeactivateUsers = async () => {
            const emails = selectedUsers.map((user: User) => {
                return user.user_email;
            });
            const doesAdminWantToDeactivateSelectedUsers = confirm(
                `Deactivate the following users? ${emails.join(" ")}`
            );
            if (doesAdminWantToDeactivateSelectedUsers) {
                for (const user of selectedUsers) {
                    await axios.delete(new URL("/user", serverUrl).toString(), {
                        withCredentials: true,
                        data: user,
                    });
                }
                clearSelection();
                refreshUsers();
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
                    <FaTrash
                        onClick={(event) => {
                            event.preventDefault();
                            confirmAndDeactivateUsers();
                        }}
                    />
                </a>
            </>
        );
    }
    const areAllSelectedUsersInactive = selectedUsers.every((user: User) => {
        return user.is_user_deactivated;
    });
    if (areAllSelectedUsersInactive) {
        const confirmAndReactivateUsers = async () => {
            const emails = selectedUsers.map((user: User) => {
                return user.user_email;
            });
            const doesAdminWantToDeactivateSelectedUsers = confirm(
                `Reactivate the following users? ${emails.join(" ")}`
            );
            if (doesAdminWantToDeactivateSelectedUsers) {
                const response = await axios.get(
                    new URL("/user", serverUrl).toString(),
                    { withCredentials: true }
                );
                console.log(response);
                for (const user of selectedUsers) {
                    await axios.put(
                        new URL("/user", serverUrl).toString(),
                        user,
                        { withCredentials: true }
                    );
                }
                clearSelection();
                refreshUsers();
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
                    <FaTrashRestore
                        onClick={(event) => {
                            event.preventDefault();
                            confirmAndReactivateUsers();
                        }}
                    />
                </a>
            </>
        );
    }
    return <></>;
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
    return (
        <>
            Welcome Admin {currentAdminUser.user_email}. Here you may create and
            deactivate users.
            <br />
            <br />
            <ManageUsers
                serverUrl={serverUrl}
                currentAdminUser={currentAdminUser}
            />
        </>
    );
};

export default AdminPanel;
