import { useEffect, useState } from "react";
import {
  View, Text, ScrollView, TouchableOpacity, TextInput,
  StyleSheet, ActivityIndicator, Alert,
} from "react-native";
import { aidesApi, type Aide } from "../../src/api/client";

const C = {
  bg: "#0f0f1a", surface: "#1a1a2e", border: "#2e2e4e",
  text: "#e8e8f0", muted: "#8888aa", primary: "#6c63ff",
  secondary: "#48cfad", warning: "#fed330", danger: "#fc5c65",
};

export default function AidesScreen() {
  const [aides, setAides] = useState<Aide[]>([]);
  const [area, setArea] = useState("attention");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  // `loading` already starts true, so the mount fetch does not need to set it
  // again synchronously inside the effect (react-hooks/set-state-in-effect).
  const load = () => {
    aidesApi.list().then(setAides).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const aide = await aidesApi.create(area);
      setAides((prev) => [...prev, aide]);
    } catch (e: unknown) {
      Alert.alert("Error", String(e));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = (id: string) => {
    Alert.alert("Remove Aide", "Are you sure?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Remove",
        style: "destructive",
        onPress: async () => {
          await aidesApi.delete(id);
          setAides((prev) => prev.filter((a) => a.aide_id !== id));
        },
      },
    ]);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Aides</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Create New Aide</Text>
        <TextInput
          style={styles.input}
          value={area}
          onChangeText={setArea}
          placeholder="Expertise area"
          placeholderTextColor={C.muted}
        />
        <TouchableOpacity
          style={[styles.btn, creating && styles.btnDisabled]}
          onPress={handleCreate}
          disabled={creating}
        >
          <Text style={styles.btnText}>{creating ? "Creating…" : "+ New Aide"}</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator color={C.primary} />
      ) : aides.length === 0 ? (
        <Text style={styles.empty}>No aides yet. Create one above.</Text>
      ) : (
        aides.map((aide) => (
          <View key={aide.aide_id} style={styles.aideCard}>
            <View style={styles.row}>
              <Text style={styles.areaName}>{aide.expertise_area}</Text>
              <TouchableOpacity onPress={() => handleDelete(aide.aide_id)}>
                <Text style={{ color: C.danger, fontSize: 12 }}>Remove</Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.idText}>{aide.aide_id.slice(0, 8)}</Text>
            <View style={styles.statsRow}>
              {[
                { label: "Total", value: aide.total_interventions, color: C.text },
                { label: "Success", value: aide.successful_interventions, color: C.secondary },
                { label: "Crisis", value: aide.crisis_interventions, color: C.danger },
                { label: "Independence", value: aide.independence_achievements, color: C.primary },
              ].map(({ label, value, color }) => (
                <View key={label} style={{ flex: 1, alignItems: "center" }}>
                  <Text style={{ color, fontWeight: "700", fontSize: 16 }}>{value}</Text>
                  <Text style={{ color: C.muted, fontSize: 10 }}>{label}</Text>
                </View>
              ))}
            </View>
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
  input: { borderWidth: 1, borderColor: C.border, borderRadius: 8, padding: 10, color: C.text, backgroundColor: "#0f0f1a", marginBottom: 10 },
  btn: { backgroundColor: C.secondary, borderRadius: 8, padding: 12, alignItems: "center" },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: "#0f0f1a", fontWeight: "700" },
  empty: { color: C.muted, textAlign: "center", marginTop: 40 },
  aideCard: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 12, padding: 16, marginBottom: 12 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 4 },
  areaName: { fontSize: 16, fontWeight: "600", color: C.text, textTransform: "capitalize" },
  idText: { fontSize: 11, color: C.muted, fontFamily: "monospace", marginBottom: 10 },
  statsRow: { flexDirection: "row" },
});
