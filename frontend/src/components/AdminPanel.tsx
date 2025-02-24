import { useCallback, useEffect, useState } from "react";
import DataTable from "react-data-table-component";
import { FaTrash, FaTrashRestore } from "react-icons/fa";
import Server from "../model/Server";
import { useNavigate } from "react-router-dom";
import { CurrentUserAndLogoutButton } from "./RightSidePanelContents";
import { CyrisLogo } from "./LeftSidePanelContents";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

function ManageUsers({
    server,
    currentAdminUser,
}: {
    server: Server;
    currentAdminUser: User;
}) {
    const [users, setUsers] = useState<User[]>([]);
    const refreshUsers = async () => {
        const response = await server.api.get<User[]>("/user", {
            withCredentials: true,
        });
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
                server={server}
                selectedUsers={selectedUsers}
                clearSelection={clearSelection}
            />
            <CreateUsers server={server} refreshUsers={refreshUsers} />
        </>
    );
}

function ManageExtensions({ server }: { server: Server }) {
    const [extensions, setExtensions] = useState<Extension[]>([]);
    const refreshExtensions = async () => {
        const response = await server.api.get<Extension[]>("/extension", {
            withCredentials: true,
        });
        setExtensions(response.data);
    };
    useEffect(() => {
        refreshExtensions();
    }, []);

    const columns = [
        {
            name: "extension_id",
            selector: (extension: Extension) => extension.extension_id,
            sortable: true,
        },
        {
            name: "Name",
            selector: (extension: Extension) => extension.name,
            sortable: true,
        },
        {
            name: "Version",
            selector: (extension: Extension) =>
                extension.metadata.installed_version,
            sortable: false,
        },
    ];

    const [selectedExtensions, setSelectedExtensions] = useState<Extension[]>(
        []
    );
    const [toggleClearSelectedExtensions, setToggleClearSelectedExtensions] =
        useState<boolean>(false);

    const uninstallSelectedExtensions = async () => {
        const confirmAndUninstallExtensions = async () => {
            const extensionNames = selectedExtensions.map(
                (extension: Extension) => {
                    return extension.name;
                }
            );
            const doesAdminWantToUninstallExtensions = confirm(
                `Uninstall the following extensions? ${extensionNames.join(
                    "\n"
                )}`
            );
            if (doesAdminWantToUninstallExtensions) {
                for (const extension of selectedExtensions) {
                    await server.api.delete("/extension", {
                        withCredentials: true,
                        params: { extension_id: extension.extension_id },
                    });
                }
                setSelectedExtensions([]);
                setToggleClearSelectedExtensions(true);
                refreshExtensions();
            }
        };
        await confirmAndUninstallExtensions();
    };

    return (
        <>
            <div style={{ padding: "20px" }}>
                <DataTable
                    columns={columns}
                    data={extensions}
                    keyField="Name"
                    striped
                    highlightOnHover
                    theme="dark"
                    pagination
                    selectableRows
                    clearSelectedRows={toggleClearSelectedExtensions}
                    onSelectedRowsChange={({
                        selectedRows,
                    }: {
                        selectedRows: Extension[];
                    }) => {
                        setSelectedExtensions(selectedRows);
                    }}
                />
                <div hidden={selectedExtensions.length == 0}>
                    <a
                        href=""
                        onClick={(event) => {
                            event.preventDefault();
                        }}
                    >
                        <FaTrash
                            onClick={(event) => {
                                event.preventDefault();
                                uninstallSelectedExtensions();
                            }}
                        />
                    </a>
                </div>
            </div>
        </>
    );
}

function CreateUsers({
    server,
    refreshUsers,
}: {
    server: Server;
    refreshUsers: () => void;
}) {
    const [usernameInput, setUsernameInput] = useState("");
    const [passwordInput, setPasswordInput] = useState("");
    const [humanNameInput, setHumanNameInput] = useState("");
    const [aiNameInput, setAiNameInput] = useState("");

    const createUser = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        event.stopPropagation();
        const openAiNameRegex = /^[a-zA-Z0-9_-]+$/;

        if (!openAiNameRegex.test(humanNameInput)) {
            alert("username must match ^[a-zA-Z0-9_-]+$");
            return;
        }

        if (!openAiNameRegex.test(aiNameInput)) {
            alert("username must match ^[a-zA-Z0-9_-]+$");
            return;
        }

        server.api.post(
            "/user",
            {
                desired_user_email: usernameInput,
                desired_user_password: passwordInput,
                desired_human_name: humanNameInput,
                desired_ai_name: aiNameInput,
            },
            { withCredentials: true }
        );
        setUsernameInput("");
        setPasswordInput("");
        setHumanNameInput("");
        setAiNameInput("");
        refreshUsers();
    };
    return (
        <>
            <h2>Create a User</h2>
            <form onSubmit={createUser}>
                <div className="inputs">
                    <input
                        type="text"
                        placeholder="user email address"
                        value={usernameInput}
                        onChange={(event) => {
                            setUsernameInput(event.target.value);
                        }}
                    ></input>
                    <br />
                    <input
                        type="password"
                        placeholder="password"
                        value={passwordInput}
                        onChange={(event) => {
                            setPasswordInput(event.target.value);
                        }}
                    ></input>
                    <br />
                    <input
                        type="text"
                        placeholder="human name"
                        value={humanNameInput}
                        onChange={(event) => {
                            setHumanNameInput(event.target.value);
                        }}
                    ></input>
                    <br />
                    <input
                        type="text"
                        placeholder="AI name"
                        value={aiNameInput}
                        onChange={(event) => {
                            setAiNameInput(event.target.value);
                        }}
                    ></input>
                </div>
                <button type="submit">Create User</button>
            </form>
        </>
    );
}

function UserManagementActionsBar({
    refreshUsers,
    selectedUsers,
    server,
    clearSelection,
}: {
    refreshUsers: () => Promise<void>;
    selectedUsers: User[];
    server: Server;
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
                    await server.api.delete("/user", {
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
                for (const user of selectedUsers) {
                    await server.api.put("/user", user, {
                        withCredentials: true,
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

const AdminPanelMainContent = ({
    server,
    currentAdminUser,
}: {
    server: Server;
    currentAdminUser: AdminUser;
}) => {
    type tabId = "manage_users" | "manage_extensions";
    const [selectedTab, setSelectedTab] = useState<tabId>("manage_users");

    const handleTabChange = (event: React.SyntheticEvent, newValue: tabId) => {
        setSelectedTab(newValue);
        (event.target as HTMLElement).blur(); // remove focus from the tab
    };

    return (
        <div className="admin-panel">
            <Tabs
                onChange={handleTabChange}
                value={selectedTab}
                textColor="inherit"
            >
                <Tab label="Users" value={"manage_users"} />
                <Tab label="Extensions" value={"manage_extensions"} />
            </Tabs>
            <div hidden={selectedTab !== "manage_users"} role="tabpanel">
                <ManageUsers
                    server={server}
                    currentAdminUser={currentAdminUser}
                />
            </div>
            <div hidden={selectedTab !== "manage_extensions"} role="tabpanel">
                <ManageExtensions server={server} />
            </div>
        </div>
    );
};

const AdminPanel = ({
    currentUser,
    server,
    setCurrentUserAndCookie,
}: {
    currentUser: User | null;
    server: Server | null;
    setCurrentUserAndCookie: (user: User | null) => void;
}) => {
    const navigate = useNavigate();
    useEffect(() => {
        if (!server || !currentUser || !currentUser.is_user_an_admin) {
            navigate("/"); // TODO put this in useEffect
            return;
        }
    }, [navigate, currentUser, server]);

    function isUserAnAdminUser(user: User | null): user is AdminUser {
        return user ? user.is_user_an_admin : false;
    }

    if (!isUserAnAdminUser(currentUser) || !server) {
        return;
    }

    return (
        <div className="app-container">
            <div className="left-side-panel">
                <CyrisLogo />
                <div>
                    Welcome Admin {currentUser.user_email}. Here you may manage
                    users and extensions.
                </div>
            </div>
            <div className="main-panel">
                <AdminPanelMainContent
                    currentAdminUser={currentUser}
                    server={server}
                />
            </div>
            <div className="right-side-panel">
                <CurrentUserAndLogoutButton
                    currentUser={currentUser}
                    server={server}
                    setCurrentUserAndCookie={setCurrentUserAndCookie}
                />
            </div>
        </div>
    );
};

export default AdminPanel;
