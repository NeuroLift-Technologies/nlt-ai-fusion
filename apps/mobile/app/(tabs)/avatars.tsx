import { useEffect, useState } from "react";
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, ActivityIndicator, Alert,
} from "react-native";
import { avatarsApi, type Avatar } from "../../src/api/client";

const C = {
  bg: "#0f0f1a", surface: "#1a1a2e", border: "#2e2e4e",
  text: "#e8e8f0", muted: "#8888aa", primary: "#6c63ff",
  secondary: "#48cfad", warning: "#fed330", danger: "#fc5c65",
};

export default function AvatarsScreen() {
  const [avatars, setAvatars] = useState<Avatar[]>([]);
  const [traits, setTraits] = useState<string[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  // `loading` already starts true, so the mount fetch does not need to set it
  // again synchronously inside the effect (react-hooks/set-state-in-effect).
  const load = () => {
    Promise.all([avatarsApi.list(), avatarsApi.traits()])
      .then(([avs, ts]) => { setAvatars(avs); setTraits(ts); })
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async () => {
    const trait = traits[selectedIdx];
    if (!trait) return;
    setCreating(true);
    try {
      const av = await avatarsApi.create(trait);
      setAvatars((prev) => [...prev, av]);
    } catch (e: unknown) {
      Alert.alert("Error", String(e));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = (id: string) => {
    Alert.alert("Remove Avatar", "Are you sure?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Remove", style: "destructive",
        onPress: async () => {
          await avatarsApi.delete(id);
          setAvatars((prev) => prev.filter((a) => a.avatar_id !== id));
        },
      },
    ]);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Avatars</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Create New Avatar</Text>
        <Text style={styles.label}>Select Trait</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 12 }}>
          {traits.map((t, i) => (
            <TouchableOpacity
              key={t}
              style={[styles.chip, selectedIdx === i && styles.chipActive]}
              onPress={() => setSelectedIdx(i)}
            >
              <Text style={[styles.chipText, selectedIdx === i && styles.chipTextActive]}>
                {t.replace(/_/g, " ")}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
        <TouchableOpacity
          style={[styles.btn, creating && styles.btnDisabled]}
          onPress={handleCreate}
          disabled={creating}
        >
          <Text style={styles.btnText}>{creating ? "Creating…" : "+ New Avatar"}</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator color={C.primary} />
      ) : avatars.length === 0 ? (
        <Text style={styles.empty}>No avatars yet. Create one above.</Text>
      ) : (
        avatars.map((av) => (
          <View key={av.avatar_id} style={styles.avatarCard}>
            <View style={styles.row}>
              <Text style={styles.traitName}>{av.trait_name.replace(/_/g, " ")}</Text>
              <TouchableOpacity onPress={() => handleDelete(av.avatar_id)}>
                <Text style={{ color: C.danger, fontSize: 12 }}>Remove</Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.state}>{av.current_state}</Text>
            <View style={styles.statsRow}>
              {[
                { label: "Attempted", value: av.total_tasks_attempted, color: C.text },
                { label: "Completed", value: av.total_tasks_completed, color: C.secondary },
                { label: "Coaching", value: av.total_coaching_sessions, color: C.warning },
              ].map(({ label, value, color }) => (
                <View key={label} style={{ flex: 1, alignItems: "center" }}>
                  <Text style={{ color, fontWeight: "700", fontSize: 18 }}>{value}</Text>
                  <Text style={{ color: C.muted, fontSize: 11 }}>{label}</Text>
                </View>
              ))}
            </View>
            {[
              { label: "Stress", value: av.stress_level, color: C.danger },
              { label: "Cognitive Load", value: av.cognitive_load, color: C.warning },
              { label: "Burnout Risk", value: av.burnout_risk_level, color: C.danger },
            ].map(({ label, value, color }) => (
              <View key={label} style={{ marginTop: 6 }}>
                <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: 2 }}>
                  <Text style={{ color: C.muted, fontSize: 11 }}>{label}</Text>
                  <Text style={{ color, fontSize: 11 }}>{(value * 100).toFixed(0)}%</Text>
                </View>
                <View style={{ height: 4, backgroundColor: C.border, borderRadius: 2, overflow: "hidden" }}>
                  <View style={{ height: 4, width: `${value * 100}%`, backgroundColor: color, borderRadius: 2 }} />
                </View>
              </View>
            ))}
          </View>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg },
  content: { padding: 16, paddingBottom: 40 },
  heading: { fontSize: 26, fontWeight: "bold", color: C.text, marginBottom: 16 },
  card: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 12, padding: 16, marginBottom: 16 },
  cardTitle: { fontSize: 15, fontWeight: "600", color: C.text, marginBottom: 10 },
  label: { fontSize: 12, color: C.muted, marginBottom: 6 },
  chip: { borderWidth: 1, borderColor: C.border, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 6, marginRight: 8, backgroundColor: "#0f0f1a" },
  chipActive: { borderColor: C.primary, backgroundColor: `${C.primary}22` },
  chipText: { color: C.muted, fontSize: 12 },
  chipTextActive: { color: C.primary, fontWeight: "600" },
  btn: { backgroundColor: C.primary, borderRadius: 8, padding: 12, alignItems: "center" },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: "#fff", fontWeight: "600" },
  empty: { color: C.muted, textAlign: "center", marginTop: 40 },
  avatarCard: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 12, padding: 16, marginBottom: 12 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 4 },
  traitName: { fontSize: 16, fontWeight: "600", color: C.text, textTransform: "capitalize" },
  state: { fontSize: 12, color: C.muted, fontFamily: "monospace", marginBottom: 10 },
  statsRow: { flexDirection: "row", marginBottom: 8 },
});
