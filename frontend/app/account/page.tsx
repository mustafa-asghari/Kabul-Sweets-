"use client";

import { FormEvent, useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";

export default function AccountPage() {
  const { user, isAuthenticated, loading, updateProfile, changePassword } = useAuth();

  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [profileSaving, setProfileSaving] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);

  useEffect(() => {
    if (!user) {
      return;
    }
    setFullName(user.full_name);
    setPhone(user.phone || "");
  }, [user]);

  const onProfileSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setProfileSaving(true);
    setProfileMessage(null);
    try {
      await updateProfile({
        full_name: fullName.trim(),
        phone: phone.trim() || undefined,
      });
      setProfileMessage("Profile updated.");
    } catch (error) {
      if (error instanceof ApiError) {
        setProfileMessage(error.detail);
      } else {
        setProfileMessage("Unable to update profile.");
      }
    } finally {
      setProfileSaving(false);
    }
  };

  const onPasswordSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setPasswordSaving(true);
    setPasswordMessage(null);
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordMessage("Password updated.");
      setCurrentPassword("");
      setNewPassword("");
    } catch (error) {
      if (error instanceof ApiError) {
        setPasswordMessage(error.detail);
      } else {
        setPasswordMessage("Unable to change password.");
      }
    } finally {
      setPasswordSaving(false);
    }
  };

  return (
    <>
      <Navbar />
      <main className="flex-1 pb-20">
        <section className="max-w-[920px] mx-auto px-6 pt-8">
          <div className="rounded-[2rem] bg-cream-dark px-6 py-12">
            <h1 className="text-4xl font-extrabold tracking-tight text-black">Account</h1>
            <p className="mt-2 text-sm text-gray-600">
              Manage your profile and password.
            </p>
          </div>
        </section>

        <section className="max-w-[920px] mx-auto px-6 pt-8 space-y-6">
          {!loading && !isAuthenticated ? (
            <div className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-6">
              <p className="text-black font-semibold">Please login to view your account.</p>
              <button
                type="button"
                onClick={() => window.dispatchEvent(new Event("open-auth-modal"))}
                className="mt-4 rounded-full bg-black px-5 py-2 text-sm font-semibold text-white"
              >
                Login / Register
              </button>
            </div>
          ) : (
            <>
              <form className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-6" onSubmit={onProfileSubmit}>
                <h2 className="text-xl font-bold tracking-tight text-black">Profile</h2>
                <div className="mt-4 grid grid-cols-1 gap-4">
                  <label className="text-sm font-semibold text-black">
                    Full Name
                    <input
                      type="text"
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      required
                      className="mt-1.5 w-full rounded-xl border border-[#e7d8c2] px-3 py-2.5 text-sm"
                    />
                  </label>
                  <label className="text-sm font-semibold text-black">
                    Phone
                    <input
                      type="text"
                      value={phone}
                      onChange={(event) => setPhone(event.target.value)}
                      className="mt-1.5 w-full rounded-xl border border-[#e7d8c2] px-3 py-2.5 text-sm"
                    />
                  </label>
                </div>
                {profileMessage ? <p className="mt-3 text-sm text-gray-600">{profileMessage}</p> : null}
                <button
                  type="submit"
                  disabled={profileSaving}
                  className="mt-4 rounded-full bg-black px-5 py-2 text-sm font-semibold text-white disabled:opacity-60"
                >
                  {profileSaving ? "Saving..." : "Save Profile"}
                </button>
              </form>

              <form className="rounded-[1.5rem] bg-white border border-[#eadcc8] p-6" onSubmit={onPasswordSubmit}>
                <h2 className="text-xl font-bold tracking-tight text-black">Change Password</h2>
                <div className="mt-4 grid grid-cols-1 gap-4">
                  <label className="text-sm font-semibold text-black">
                    Current Password
                    <input
                      type="password"
                      value={currentPassword}
                      onChange={(event) => setCurrentPassword(event.target.value)}
                      required
                      className="mt-1.5 w-full rounded-xl border border-[#e7d8c2] px-3 py-2.5 text-sm"
                    />
                  </label>
                  <label className="text-sm font-semibold text-black">
                    New Password
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(event) => setNewPassword(event.target.value)}
                      required
                      minLength={8}
                      className="mt-1.5 w-full rounded-xl border border-[#e7d8c2] px-3 py-2.5 text-sm"
                    />
                  </label>
                </div>
                {passwordMessage ? <p className="mt-3 text-sm text-gray-600">{passwordMessage}</p> : null}
                <button
                  type="submit"
                  disabled={passwordSaving}
                  className="mt-4 rounded-full bg-black px-5 py-2 text-sm font-semibold text-white disabled:opacity-60"
                >
                  {passwordSaving ? "Updating..." : "Update Password"}
                </button>
              </form>
            </>
          )}
        </section>
      </main>
      <Footer />
    </>
  );
}
