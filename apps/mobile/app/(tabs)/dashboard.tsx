import { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { router } from "expo-router";
import { api } from "@/lib/api";
import type { SessionSummary } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  pending: "#fbbf24",
  running: "#3b82f6",
  completed: "#22c55e",
  failed: "#ef4444",
  aborted: "#9ca3af",
};

export default function DashboardScreen() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const data = await api.sessions.list();
      setSessions(data);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  };

  // Resolve the mount fetch in promise callbacks instead of calling load()
  // directly in the effect body (react-hooks/set-state-in-effect), and ignore
  // results that arrive after unmount.
  useEffect(() => {
    let active = true;
    api.sessions
      .list()
      .then((data) => {
        if (!active) return;
        setSessions(data);
        setError(null);
      })
      .catch((e: unknown) => {
        if (!active) return;
        setError(e instanceof Error ? e.message : "Failed to load");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#4f46e5" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <View style={styles.header}>
        <Text style={styles.title}>Dashboard</Text>
        <TouchableOpacity
          style={styles.newBtn}
          onPress={() => router.push("/session/new")}
        >
          <Text style={styles.newBtnText}>+ New Session</Text>
        </TouchableOpacity>
      </View>

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      {sessions.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyText}>No training sessions yet.</Text>
          <TouchableOpacity onPress={() => router.push("/session/new")}>
            <Text style={styles.emptyLink}>Start your first session →</Text>
          </TouchableOpacity>
        </View>
      ) : (
        sessions.map((s) => (
          <TouchableOpacity
            key={s.session_id}
            style={styles.card}
            onPress={() => router.push(`/session/${s.session_id}`)}
          >
            <View style={styles.cardTop}>
              <Text style={styles.cardId}>{s.session_id.slice(0, 8)}…</Text>
              <View style={[styles.badge, { backgroundColor: STATUS_COLORS[s.status] ?? "#9ca3af" }]}>
                <Text style={styles.badgeText}>{s.status}</Text>
              </View>
            </View>
            <Text style={styles.cardAvatar}>{s.avatar_type.replace(/_/g, " ")}</Text>
            <Text style={styles.cardAide}>{s.aide_type.replace(/_/g, " ")}</Text>
            <Text style={styles.cardDate}>{new Date(s.created_at).toLocaleString()}</Text>
          </TouchableOpacity>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb", padding: 16 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  title: { fontSize: 22, fontWeight: "700", color: "#111827" },
  newBtn: { backgroundColor: "#4f46e5", paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8 },
  newBtnText: { color: "#fff", fontWeight: "600", fontSize: 13 },
  errorBox: { backgroundColor: "#fee2e2", padding: 12, borderRadius: 8, marginBottom: 12 },
  errorText: { color: "#b91c1c", fontSize: 13 },
  empty: { alignItems: "center", paddingVertical: 60 },
  emptyText: { color: "#6b7280", marginBottom: 8 },
  emptyLink: { color: "#4f46e5", fontWeight: "600" },
  card: { backgroundColor: "#fff", borderRadius: 12, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: "#e5e7eb" },
  cardTop: { flexDirection: "row", justifyContent: "space-between", marginBottom: 8 },
  cardId: { fontSize: 12, fontFamily: "monospace", color: "#9ca3af" },
  badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 12 },
  badgeText: { color: "#fff", fontSize: 11, fontWeight: "600" },
  cardAvatar: { fontSize: 15, fontWeight: "600", color: "#111827", textTransform: "capitalize" },
  cardAide: { fontSize: 13, color: "#6b7280", textTransform: "capitalize", marginTop: 2 },
  cardDate: { fontSize: 11, color: "#9ca3af", marginTop: 6 },
});
