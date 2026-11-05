export function NotMember({ email }: { email: string | null }) {
  return (
    <main className="shell">
      <div className="card">
        <h1 style={{ fontSize: 22 }}>You're signed in, but not on the list yet</h1>
        <p className="muted">
          {email ? <>The account <strong>{email}</strong> is </> : "This account is "}
          not a member of this workspace. Ask an owner to add you, then reload this page.
        </p>
      </div>
    </main>
  );
}
