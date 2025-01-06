import "../assets/SignedInAs.css";

function SignedInAs({
    myUser,
    setMyUser,
}: {
    myUser: User | null;
    setMyUser: (user: User | null) => void;
}) {
    return (
        <>
            <div className="signed-in-as">
                <p>
                    {myUser
                        ? "Signed in as " + myUser.human_name
                        : "Not signed in."}
                </p>
                {myUser && (
                    <p>
                        Not you?{" "}
                        <a
                            href=""
                            onClick={(event) => {
                                event.preventDefault();
                                setMyUser(null);
                            }}
                        >
                            Sign out
                        </a>
                    </p>
                )}
            </div>
        </>
    );
}

export default SignedInAs;
