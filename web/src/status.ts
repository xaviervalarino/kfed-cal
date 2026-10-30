import { mount } from "svelte";
import "./app.css";
import Status from "./Status.svelte";

mount(Status, { target: document.getElementById("app")! });
