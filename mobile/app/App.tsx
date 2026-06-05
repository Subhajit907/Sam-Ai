/**
 * Alia AI — Mobile App root
 * Bottom tab navigation: Chat | Settings
 */

import React from "react";
import { Platform, StatusBar } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { MaterialIcons } from "@expo/vector-icons";
import ChatScreen    from "./src/screens/ChatScreen";
import SettingsScreen from "./src/screens/SettingsScreen";

const Tab = createBottomTabNavigator();

const BG     = "#04040f";
const BLUE   = "#00b4ff";
const DIM    = "#4488aa";
const BORDER = "#1a3a5c";

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar barStyle="light-content" backgroundColor={BG} />
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerStyle:      { backgroundColor: BG, borderBottomColor: BORDER, borderBottomWidth: 1 },
          headerTintColor:  BLUE,
          headerTitleStyle: {
            fontFamily: Platform.select({ ios: "Courier", android: "monospace" }),
            fontSize: 14,
            fontWeight: "bold",
          },
          tabBarStyle:            { backgroundColor: BG, borderTopColor: BORDER, borderTopWidth: 1 },
          tabBarActiveTintColor:  BLUE,
          tabBarInactiveTintColor: DIM,
          tabBarLabelStyle: {
            fontFamily: Platform.select({ ios: "Courier", android: "monospace" }),
            fontSize: 10,
          },
          tabBarIcon: ({ color, size }) => {
            const icons: Record<string, any> = {
              Chat:     "chat-bubble-outline",
              Settings: "settings",
            };
            return <MaterialIcons name={icons[route.name]} size={size} color={color} />;
          },
        })}
      >
        <Tab.Screen name="Chat"     component={ChatScreen}     options={{ title: "ALIA AI" }} />
        <Tab.Screen name="Settings" component={SettingsScreen} options={{ title: "SETTINGS" }} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
