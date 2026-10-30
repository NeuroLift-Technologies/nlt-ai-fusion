import { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { router } from "expo-router";
import { api } from "@/lib/api";
import type { SessionSummary } from "@/lib/types";

export default function SessionsScreen() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    const data = await api.sessions.list();
    setSessions(data);
  };

  // Resolve the mount fetch in promise callbacks instead of calling load()
  // directly in the effect body (react-hooks/set-state-in-effect), and ignore
  // results that arrive after unmount.
  useEffect(() => {
    let active = true;
    api.sessions
      .list()
      .then((data) => {
        if (active) setSessions(data);
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
    <View style={styles.container}>
      <FlatList
        data={sessions}
        keyExtractor={(item) => item.session_id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No sessions yet.</Text>
          </View>
        }
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={styles.title}>All Sessions</Text>
            <TouchableOpacity style={styles.newBtn} onPress={() => router.push("/session/new")}>
              <Text style={styles.newBtnText}>New</Text>
            </TouchableOpacity>
          </View>
        }
        renderItem={({ item: s }) => (
          <TouchableOpacity style={styles.row} onPress={() => router.push(`/session/${s.session_id}`)}>
            <View style={{ flex: 1 }}>
              <Text style={styles.rowId}>{s.session_id.slice(0, 12)}…</Text>
              <Text style={styles.rowAvatar}>{s.avatar_type.replace(/_/g, " ")}</Text>
            </View>
            <Text style={[styles.status, { color: statusColor(s.status) }]}>{s.status}</Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

function statusColor(s: string) {
  const map: Record<string, string> = {
    pending: "#f59e0b",
    running: "#3b82f6",
    completed: "#22c55e",
    failed: "#ef4444",
    aborted: "#9ca3af",
  };
  return map[s] ?? "#9ca3af";
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 16, paddingBottom: 8 },
  title: { fontSize: 20, fontWeight: "700", color: "#111827" },
  newBtn: { backgroundColor: "#4f46e5", paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8 },
  newBtnText: { color: "#fff", fontWeight: "600", fontSize: 13 },
  row: { flexDirection: "row", alignItems: "center", backgroundColor: "#fff", marginHorizontal: 16, marginBottom: 8, padding: 14, borderRadius: 10, borderWidth: 1, borderColor: "#e5e7eb" },
  rowId: { fontSize: 11, fontFamily: "monospace", color: "#9ca3af" },
  rowAvatar: { fontSize: 14, fontWeight: "600", color: "#111827", textTransform: "capitalize", marginTop: 2 },
  status: { fontSize: 12, fontWeight: "600", textTransform: "capitalize" },
  empty: { alignItems: "center", paddingTop: 80 },
  emptyText: { color: "#6b7280" },
});
